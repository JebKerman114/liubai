桌面待办与便签。支持置顶、自动保存、托盘和深浅色主题。

| 系统 | 架构 | 下载格式 |
| --- | --- | --- |
| Windows | x64、ARM64 | 安装 EXE、MSI、便携 ZIP、未签名 MSIX |
| Linux | x86_64、aarch64 | AppImage、DEB、RPM、Arch 包、TAR.GZ、Flatpak、Snap |

Windows x64 需要 Windows 10 2004+；Windows ARM64 需要 Windows 11。Linux 原生包需要 glibc 2.39+，例如 Ubuntu 24.04+、Debian 13+、较新的 Fedora / Arch。Linux 置顶适配 X11 / XWayland；Wayland 原生协议下的跨桌面置顶不作保证。

- Windows 普通用户推荐 `-setup.exe` 或 `-portable.zip`。EXE / MSI 未代码签名；MSIX 标记为 `-unsigned.msix`，须由使用者以受信任证书签名后部署，不附带证书或私钥。
- Linux 推荐 AppImage；DEB 用于 Debian / Ubuntu，RPM 用于 Fedora 等，`pkg.tar.zst` 用于 Arch。
- Flatpak 安装：先配置 Flathub，再执行 `flatpak install --user ./liubai-*.flatpak`，需要 KDE Platform 6.10。
- Snap 安装：`sudo snap install --dangerous --classic ./liubai-*.snap`。这是供本地安装的 classic 包，未发布到 Snap Store。
- AppImage 可使用 `--appimage-extract-and-run` 在没有 FUSE 的环境中运行。
- `SHA256SUMS` 用于核对下载文件。每个架构均在对应的原生 GitHub Actions 构建机上打包，并运行控件测试和打包程序启动测试。

数据与程序分离：Linux 默认 `~/.local/share/liubai`，Windows 默认 `%LOCALAPPDATA%\Liubai`。安装包不包含个人待办或便签。
