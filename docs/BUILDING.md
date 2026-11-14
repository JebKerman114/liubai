# 构建与发布

| 目标 | GitHub 构建机 | 输出 |
| --- | --- | --- |
| Linux x86_64 | ubuntu-24.04 | TAR.GZ、DEB、RPM、Arch、AppImage、Flatpak、Snap |
| Linux aarch64 | ubuntu-24.04-arm | 同上 |
| Windows x64 | windows-2025 | ZIP、EXE、MSI、未签名 MSIX |
| Windows ARM64 | windows-11-arm | 同上 |

全部使用对应架构的 Python 3.12。不跨平台重命名二进制文件。`scripts/smoke_bundle.py` 校验 ELF / PE 架构并启动实际打包程序，使用临时目录验证初始化、保存及退出。

## Linux

在 Ubuntu 24.04 或同等 glibc 环境、目标架构上执行：

```sh
sudo apt-get update
sudo apt-get install -y python3-venv binutils curl libegl1 libgl1 libxcb-cursor0 libxkbcommon0 libdbus-1-3 fonts-noto-cjk flatpak ostree squashfs-tools zstd
python3 -m venv .venv-build
.venv-build/bin/python -m pip install -r requirements-build.txt
.venv-build/bin/python scripts/build.py
QT_QPA_PLATFORM=offscreen .venv-build/bin/python scripts/smoke_bundle.py
.venv-build/bin/python scripts/package_linux.py
```

只构建部分格式可用 `--formats native appimage`。`native` 同时生成 DEB、RPM、Arch 包。nFPM 2.49.0 和 appimagetool 1.9.1 会自动下载到 `.tools/` 并检查校验和。AppImage 生成过程还会获取上游 type2 runtime。

Flatpak 直接把现有动态程序包导出到本地 OSTree 仓库并生成 bundle，运行时依赖 KDE Platform 6.10。Snap 直接生成 SquashFS，含 `meta/snap.yaml`，使用 `core24` 和 `classic`。没有自动执行商店提交。

## Windows

在对应架构的 Windows 上安装 Python 3.12、Inno Setup 6、.NET SDK 8+、Windows SDK：

```powershell
python -m venv .venv-build
.venv-build\Scripts\python -m pip install -r requirements-build.txt
dotnet tool install --global wix --version 6.0.2
.venv-build\Scripts\python scripts/build.py
.venv-build\Scripts\python scripts/smoke_bundle.py
.venv-build\Scripts\python scripts/package_windows.py
```

Inno Setup 生成当前用户安装 EXE，WiX 生成系统范围 MSI，Windows SDK MakeAppx 生成未签名 MSIX。便携 ZIP 内的 `liubai.exe` 需要同目录运行库，需保留整个目录。

代码签名证书不在仓库中。MSIX 使用 `CN=Liubai` 作为默认发布者，供使用者修改为自己的证书身份并签名；不能把未签名 MSIX 当作可直接安装的正式签名包。

## GitHub Actions

手动运行 `.github/workflows/build.yml`。`release_tag` 留空仅上传 Actions artifacts；提供 `v<程序版本>` 时，四个目标全部成功后才发布 Release。推送 `v*` 标签也可触发发布。

发布前检查总数必须为 22，随后生成统一 `SHA256SUMS`。失败的构建不会发布部分 Release。每个目标的控件截图保存在单独的 preview artifact 中。
