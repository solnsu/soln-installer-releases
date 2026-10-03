Soln desktop installer 1.0.0 preview for deploying a tenant Runtime on your own computer. / Soln 本地租户 Runtime 安装器 1.0.0 预览版。

| Platform / 平台 | Download / 下载文件 |
| --- | --- |
| macOS Apple silicon / Apple 芯片 | `Soln-1.0.0-arm64.dmg` |
| macOS Intel | `Soln-1.0.0.dmg` |
| Windows x64 | `Soln.Setup.1.0.0.exe` |
| Linux x64 | `Soln-1.0.0.AppImage` |
| Linux ARM64 | `Soln-1.0.0-arm64.AppImage` |
| Debian / Ubuntu x64 | `soln-installer-1.0.0-amd64.deb` |
| Debian / Ubuntu ARM64 | `soln-installer-1.0.0-arm64.deb` |

Prerequisites / 使用前提：Docker Desktop (macOS / Windows) or Docker Engine (Linux), and access to the Soln Control Plane and required image registries.

Install guide / 安装说明：https://help.solncn.com/en/docs/deployment-operations/local/install

Preview status / 预览版说明：These existing local builds do not yet have production platform signing verified; the macOS build has no Developer ID signing or notarization verified. The operating system may report an unverified publisher. These files are published as a prerelease. / 当前本地构建尚未完成正式平台签名验证，macOS 包尚未确认 Developer ID 签名及公证；操作系统可能提示发布者未验证，因此以预览版发行。

Validation / 验证：The packaged installer source for all five platform/architecture variants matches the current local installer source. All 13 installer tests pass. Cross-platform installation has not been retested for this release. / 五种平台与架构的包内安装器源码与当前本地源码一致，13 项安装器测试通过；本次尚未重新进行各平台实际安装测试。

Integrity / 完整性：`SHA256SUMS.txt` contains the SHA-256 checksum for every installer attachment.

### Public dependencies / 公共依赖包

| Package / 包名 | Contents / 内容 |
| --- | --- |
| `soln-public-deps-linux-amd64.tar.gz` | Linux AMD64 / x86_64 公共依赖镜像 |
| `soln-public-deps-linux-arm64.tar.gz` | Linux ARM64 公共依赖镜像 |
| `soln-public-deps-sources.tar.gz` | 第三方声明及 MinIO、mc 对应源码 |

Both image packages include / 两个镜像包均包含：PostgreSQL `17-alpine`、MinIO `RELEASE.2025-09-07T16-13-09Z`、MinIO 客户端 `RELEASE.2025-08-13T08-35-41Z`、Temporal `1.28.1`、nginx `1.29-alpine`。
