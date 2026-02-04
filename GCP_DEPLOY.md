# GCP 部署指南

本指南将帮助您将量化监控系统部署到 Google Cloud Platform (GCP)。我们推荐使用 **Cloud Run**，因为它支持无服务器容器，非常适合 Streamlit 应用，且成本较低。

## 准备工作

1.  **Google Cloud 账号**: 确保您拥有一个激活了计费功能的 GCP 账号。
2.  **创建项目**: 在 GCP 控制台创建一个新项目，记录下 `PROJECT_ID`。
3.  **安装 gcloud CLI**: 在您的本地机器上安装 Google Cloud SDK。
    *   Mac: `brew install --cask google-cloud-sdk`
    *   Windows: 下载安装包

## 部署步骤

### 方法一：使用自动化脚本 (推荐)

1.  打开终端，进入项目目录。
2.  登录您的 GCP 账号：
    ```bash
    gcloud auth login
    ```
3.  运行部署脚本 (将 `YOUR_PROJECT_ID` 替换为您的真实项目ID)：
    ```bash
    ./deploy_gcp.sh YOUR_PROJECT_ID
    ```
    *   脚本会自动启用必要服务、构建 Docker 镜像并部署到 Cloud Run。
    *   部署完成后，终端会显示访问链接。

### 方法二：手动部署 (App Engine)

如果您更喜欢使用 App Engine (无需 Docker 知识)：

1.  确保目录中有 `app.yaml` 文件。
2.  运行命令：
    ```bash
    gcloud app deploy app.yaml --project YOUR_PROJECT_ID
    ```

## 常见问题

*   **端口问题**: Streamlit 默认运行在 8501 端口。我们的 `Dockerfile` 和 `deploy_gcp.sh` 已经配置好了端口转发。
*   **权限问题**: 如果脚本提示权限错误，请确保您已登录 (`gcloud auth login`) 并设置了正确的项目 (`gcloud config set project YOUR_PROJECT_ID`)。
*   **成本**: Cloud Run 按使用量计费，对于个人监控项目，通常在免费额度内或费用极低。
