# 部署到 Google Cloud Run 指南

本项目非常适合部署在 Google Cloud Run，因为它支持容器化部署，且可以通过配置保持后台线程运行。

## 前置准备

1.  **Google Cloud 账号**: 确保你有一个活跃的 Google Cloud 项目。
2.  **gcloud CLI**: 确保本地已安装并登录了 Google Cloud SDK。
    *   登录命令: `gcloud auth login`
    *   设置项目: `gcloud config set project YOUR_PROJECT_ID`

## 部署步骤

### 方法一：使用自动化脚本 (推荐)

我们准备了一个一键部署脚本 `deploy_gcp.sh`。

1.  **设置项目 ID**:
    ```bash
    export PROJECT_ID="你的项目ID"
    ```
    *(你可以在 Google Cloud Console 的首页找到项目 ID)*

2.  **运行脚本**:
    ```bash
    chmod +x deploy_gcp.sh
    ./deploy_gcp.sh
    ```

3.  **等待完成**:
    脚本会自动构建 Docker 镜像，推送到 Google Container Registry，并部署到 Cloud Run。
    完成后，终端会显示访问 URL。

### 方法二：手动部署

如果你想了解每一步发生了什么，可以手动执行以下命令：

1.  **启用服务**:
    ```bash
    gcloud services enable cloudbuild.googleapis.com run.googleapis.com
    ```

2.  **构建镜像**:
    ```bash
    gcloud builds submit --tag gcr.io/YOUR_PROJECT_ID/crypto-monitor
    ```

3.  **部署服务**:
    ```bash
    gcloud run deploy crypto-monitor \
      --image gcr.io/YOUR_PROJECT_ID/crypto-monitor \
      --platform managed \
      --region us-central1 \
      --allow-unauthenticated \
      --no-cpu-throttling \
      --min-instances 1 \
      --port 8080
    ```

### 关键配置说明

*   **`--no-cpu-throttling`**: 这个参数至关重要。默认情况下，Cloud Run 会在没有 HTTP 请求时冻结 CPU，这会导致我们的后台监控线程暂停。启用此选项后，CPU 会一直分配，确保后台每 5 分钟的自动更新正常运行。
*   **`--min-instances 1`**: 确保至少有一个实例一直在运行，避免冷启动，并保持后台监控持续在线。

## 成本提示

由于开启了 `no-cpu-throttling` 和 `min-instances 1`，即使没有用户访问，该服务也会持续消耗计算资源。请关注 Google Cloud 的计费情况。Cloud Run 有免费层级，但持续运行可能会超出免费额度。
