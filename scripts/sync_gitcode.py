"""Mirror GitHub release binaries to GitCode; verify every attachment by SHA-256."""
import hashlib
import json
import os
from pathlib import Path
import re
import tempfile
import time
import urllib.error
import urllib.parse
import urllib.request


class SyncError(Exception):
    pass


class SafeRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        redirected = super().redirect_request(req, fp, code, msg, headers, newurl)
        if redirected and urllib.parse.urlsplit(req.full_url).netloc != urllib.parse.urlsplit(newurl).netloc:
            redirected.remove_header('Authorization')
        return redirected


OPENER = urllib.request.build_opener(SafeRedirect())


def request_json(url, token, method='GET', body=None, missing_ok=False):
    payload = None if body is None else json.dumps(body).encode()
    headers = {'User-Agent': 'Soln-release-sync', 'Accept': 'application/json',
               'Authorization': f'Bearer {token}'}
    if payload is not None:
        headers['Content-Type'] = 'application/json'
    for attempt in range(4):
        try:
            req = urllib.request.Request(url, data=payload, headers=headers, method=method)
            with OPENER.open(req, timeout=90) as response:
                return json.load(response)
        except urllib.error.HTTPError as error:
            if error.code == 404 and missing_ok:
                return None
            if method != 'GET' or error.code not in (429, 500, 502, 503, 504) or attempt == 3:
                raise SyncError(f'{method} API request failed: HTTP {error.code}') from None
        except (urllib.error.URLError, TimeoutError):
            if method != 'GET' or attempt == 3:
                raise SyncError(f'{method} API request failed: network error') from None
        time.sleep(2 ** attempt)


def safe_name(name):
    if not isinstance(name, str) or not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9._-]{0,200}', name):
        raise SyncError('Invalid attachment filename')
    return name


def file_hash(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def download(url, destination, expected_size=None):
    if urllib.parse.urlsplit(url).scheme != 'https':
        raise SyncError('Download URL must use HTTPS')
    for attempt in range(4):
        try:
            req = urllib.request.Request(url, headers={'User-Agent': 'Soln-release-sync'})
            with OPENER.open(req, timeout=180) as response, destination.open('wb') as stream:
                content_type = response.headers.get('Content-Type', '').lower()
                if 'text/html' in content_type:
                    raise SyncError('Download returned an HTML page instead of an attachment')
                received = 0
                while chunk := response.read(1024 * 1024):
                    received += len(chunk)
                    if expected_size is not None and received > expected_size:
                        raise SyncError('Downloaded attachment exceeds expected size')
                    stream.write(chunk)
            if expected_size is not None and received != expected_size:
                raise SyncError('Downloaded attachment size mismatch')
            return
        except urllib.error.HTTPError as error:
            if error.code not in (429, 500, 502, 503, 504) or attempt == 3:
                raise SyncError(f'Public attachment download failed: HTTP {error.code}') from None
        except (urllib.error.URLError, TimeoutError):
            if attempt == 3:
                raise SyncError('Attachment download failed: network error') from None
        time.sleep(2 ** attempt)


def checksums(text, binary_names):
    result = {}
    for line in text.splitlines():
        match = re.fullmatch(r'([0-9a-f]{64})  (.+)', line)
        if not match:
            raise SyncError('Invalid SHA256SUMS.txt entry')
        digest, name = match.groups()
        safe_name(name)
        if name in result:
            raise SyncError('Duplicate checksum filename')
        result[name] = digest
    if set(result) != set(binary_names):
        raise SyncError('Checksum file does not cover exactly the release installers')
    return result


def upload(slot, path):
    url = slot['url']
    if urllib.parse.urlsplit(url).scheme != 'https':
        raise SyncError('Upload URL must use HTTPS')
    # GitCode returns a signed URL and required headers; never print either.
    data = path.read_bytes()
    for attempt in range(3):
        try:
            req = urllib.request.Request(url, data=data, headers=slot['headers'], method='PUT')
            with OPENER.open(req, timeout=600) as response:
                response.read()
            return
        except (urllib.error.URLError, TimeoutError):
            if attempt == 2:
                raise SyncError(f'Upload failed for {path.name}') from None
            time.sleep(2 ** attempt)


def sync():
    github_repo = os.environ['GITHUB_REPOSITORY']
    mirror_repo = os.environ['GITCODE_REPOSITORY']
    tag = os.environ['RELEASE_TAG']
    github_token = os.environ['GITHUB_TOKEN']
    mirror_token = os.environ.get('GITCODE_TOKEN', '')
    if not mirror_token:
        raise SyncError('Repository secret GITCODE_TOKEN is missing')
    if not re.fullmatch(r'[A-Za-z0-9._-]+/[A-Za-z0-9._-]+', mirror_repo):
        raise SyncError('Invalid GitCode repository')
    if not re.fullmatch(r'v\d+\.\d+\.\d+(?:-[A-Za-z0-9.-]+)?', tag):
        raise SyncError('Invalid release tag')
    encoded_tag = urllib.parse.quote(tag, safe='')
    source = request_json(f'https://api.github.com/repos/{github_repo}/releases/tags/{encoded_tag}', github_token)
    if source['draft']:
        raise SyncError('Draft GitHub releases cannot be mirrored')
    assets = source['assets']
    names = [safe_name(a['name']) for a in assets]
    if len(set(names)) != len(names) or 'SHA256SUMS.txt' not in names:
        raise SyncError('Release requires unique filenames and SHA256SUMS.txt')
    binary_names = [n for n in names if n != 'SHA256SUMS.txt']
    if not binary_names or any(not n.endswith(('.dmg', '.exe', '.AppImage', '.deb', '.zip')) for n in binary_names):
        raise SyncError('Release contains unsupported attachments')
    mirror_api = f'https://api.gitcode.com/api/v5/repos/{mirror_repo}'
    repository = request_json(mirror_api, mirror_token)
    if repository.get('private') is True:
        raise SyncError('GitCode distribution repository must be public')

    with tempfile.TemporaryDirectory(prefix='soln-release-sync-') as directory:
        local = Path(directory)
        for asset in assets:
            print(f'Downloading source: {asset["name"]}', flush=True)
            download(asset['browser_download_url'], local / asset['name'], asset['size'])
            if asset.get('digest') != 'sha256:' + file_hash(local / asset['name']):
                raise SyncError(f'GitHub digest mismatch: {asset["name"]}')
        expected = checksums((local / 'SHA256SUMS.txt').read_text(), binary_names)
        for name, digest in expected.items():
            if file_hash(local / name) != digest:
                raise SyncError(f'Checksum mismatch: {name}')

        release_path = mirror_api + '/releases'
        existing = request_json(release_path + '/tags/' + encoded_tag, mirror_token, missing_ok=True)
        payload = {'tag_name': tag, 'name': source['name'], 'body': source['body'] or '',
                   'release_status': 'pre'}
        if existing is None:
            payload['target_commitish'] = repository['default_branch']
            existing = request_json(release_path, mirror_token, 'POST', payload)
        mirror_names = {a['name'] for a in existing['assets']}
        report = []
        for asset in assets:
            name = asset['name']
            if name not in mirror_names:
                print(f'Uploading mirror: {name}', flush=True)
                query = urllib.parse.urlencode({'file_name': name})
                slot = request_json(release_path + '/' + encoded_tag + '/upload_url?' + query, mirror_token)
                upload(slot, local / name)
            print(f'Checking public mirror download: {name}', flush=True)
            url = release_path + '/' + encoded_tag + '/attach_files/' + urllib.parse.quote(name, safe='') + '/download'
            copy = local / ('verify-' + name)
            download(url, copy, asset['size'])
            if file_hash(copy) != file_hash(local / name):
                raise SyncError(f'Mirror digest mismatch: {name}; refusing to overwrite an existing attachment')
            report.append({'name': name, 'url': url, 'sha256': file_hash(copy), 'size': asset['size']})
            copy.unlink()
        payload['release_status'] = 'pre' if source['prerelease'] else 'latest'
        request_json(release_path + '/' + encoded_tag, mirror_token, 'PATCH', payload)
        final = request_json(release_path + '/tags/' + encoded_tag, mirror_token)
        if not set(names).issubset({a['name'] for a in final['assets']}):
            raise SyncError('Mirror release is missing attachments after upload')
        if final['name'] != source['name'] or final['body'] != (source['body'] or ''):
            raise SyncError('Mirror release metadata mismatch')
        Path('mirror-downloads.json').write_text(json.dumps(report, indent=2) + '\n')
        summary = os.environ.get('GITHUB_STEP_SUMMARY')
        if summary:
            with open(summary, 'a') as stream:
                stream.write(f'## GitCode mirror verified: {tag}\n\n')
                for item in report:
                    stream.write(f'- [{item["name"]}]({item["url"]}) — SHA-256 verified, public download verified\n')
        print(f'Sync complete: {mirror_repo}, {tag}, {len(report)} verified attachments', flush=True)


if __name__ == '__main__':
    try:
        sync()
    except (SyncError, KeyError, ValueError) as error:
        print(f'::error::{error}', flush=True)
        raise SystemExit(1) from None
