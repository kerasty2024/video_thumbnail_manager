# Video Thumbnail Manager

**Language / 言語 / 语言**:  
🇬🇧 [English](#video-thumbnail-manager-en) | 🇯🇵 [日本語](#ビデオサムネイルマネージャー-ja) | 🇨🇳 [简体中文](#视频缩略图管理器-zh)

---

<!-- English section -->
<a id="video-thumbnail-manager-en"></a>
## Video Thumbnail Manager (English)

![Screenshot](contents/example/screenshot_output_tab_1.jpg)

A Python application using FFmpeg and a **PyQt6-based** graphical user interface (GUI) for managing videos and thumbnails. This tool is designed to efficiently process video files, generate thumbnails, and provide a user-friendly interface for managing video collections.

## Features
- **Advanced Thumbnail Generation**: Generate multiple thumbnails per video for any format supported by FFmpeg.
- **GPU Acceleration (CUDA)**: Utilizes CUDA hardware acceleration for faster thumbnail generation, with robust fallback mechanisms to CPU processing for problematic videos or unsupported hardware.
- **Intelligent Caching**: Caches generated thumbnails and associated metadata. Cache is invalidated if generation parameters (e.g., thumbnail count, width, quality, distribution settings) change, ensuring up-to-date previews.
- **Responsive PyQt6 GUI**:
    - **Tabbed Interface**: Separate tabs for Input settings, Output display, and Process monitoring.
    - **Output Tab**:
        - Displays generated thumbnails in a scrollable grid.
        - Allows selection of multiple videos via checkboxes.
        - Actions: Delete selected videos (and their caches), Delete unselected videos, Clear all selections. These actions are available even during thumbnail generation.
        - Sorting: Sort videos by original order, name, size, duration, or date modified.
        - Jumping: Jump to a specific video by its current display number or search by keyword in filenames/paths.
        - Zoom: Hover over thumbnails with Ctrl key pressed to see a magnified preview.
        - Path Display: Toggle between showing full path or just filename.
        - Adjustable scroll speed.
- **Configurable Processing**:
    - **Input Tab**: Extensive settings for thumbnail generation (number per video, width, quality), video filtering (min duration, min size), and processing (concurrent videos).
    - **Thumbnail Distribution**: Choose how thumbnails are selected from the video's timeline:
        - **Uniform**: Evenly spaced thumbnails.
        - **Peak-Concentration**: (Triangular or Normal distribution) Focus thumbnail generation around a specific point in the video, adjustable peak position and concentration.
    - **Video Scanning Filters**:
        - Exclude videos based on minimum file size and duration.
        - Exclude files/folders containing specific keywords or matching regular expressions. Options to match against full path or just name.
- **Background Processing**: Thumbnail scanning and generation run in a background worker thread, keeping the GUI responsive.
- **Real-time Feedback**:
    - **Progress Bar & ETA**: Overall progress and estimated time remaining for the batch.
    - **Process Tab**: Displays FFmpeg commands being executed and shows a live preview of the currently generating thumbnail. Also logs scan duration and total thumbnail generation time.
- **Configuration Management**: Settings are saved in `config.json` and loaded on startup. GUI changes update this file.
- **Error Handling & Logging**: Detailed logging to `debug.log` and robust FFmpeg command execution with multiple fallback strategies.
- **Cross-Platform**: Designed to work on Windows, macOS, and Linux (where Python, PyQt6, and FFmpeg are available).
- **Sponsorship & Crypto Support**: Options to support the project via GitHub Sponsors, Buy Me a Coffee, or cryptocurrency donations, with QR codes and addresses displayed in the GUI.

## Requirements
- **Python**: 3.8 or higher.
- **FFmpeg**: Must be installed and accessible via the system's PATH.
    - Download from [FFmpeg.org](https://ffmpeg.org/) or install via a package manager (e.g., `apt install ffmpeg`, `brew install ffmpeg`).
    - For GPU acceleration, an FFmpeg build with CUDA support is required (along with an NVIDIA GPU and drivers).
- **Python Packages**: Install dependencies from `requirements.txt`:
    ```bash
    pip install -r requirements.txt
    ```
    Key dependencies include:
    - `PyQt6` (for the GUI)
    - `Pillow` (for image manipulation)
    - `loguru` (for logging)
    - `numpy` (for thumbnail distribution calculations)
- **Hardware (for CUDA)**: NVIDIA GPU with CUDA support and compatible drivers (optional, but highly recommended for performance).

## Installation
Windows users can often find a pre-built executable on the project's Release page. To run from source:

1.  **Clone the Repository**:
    ```bash
    git clone https://github.com/kerasty2024/video_thumbnail_manager.git
    cd video_thumbnail_manager
    ```
2.  **Set up a Virtual Environment (Recommended)**:
    ```bash
    python -m venv .venv
    # Activate it:
    # Windows: .venv\Scripts\activate
    # macOS/Linux: source .venv/bin/activate
    ```
3.  **Install Python Dependencies**:
    ```bash
    pip install -r requirements.txt
    ```
4.  **Install FFmpeg**:
    -   Ensure it's in your system PATH.
    -   Verify with `ffmpeg -version`.
5.  **Verify CUDA Support in FFmpeg (Optional)**:
    -   Run `ffmpeg -hwaccels` in your terminal. `cuda` should be listed if FFmpeg was compiled with CUDA support.
    -   Ensure your NVIDIA drivers are up-to-date.

## Usage
1.  **Run the Application**:
    ```bash
    python src/main.py
    ```
    (Or `python main.py` if you are in the `src` directory, though running from project root is standard).
2.  **Configure Settings (Input Tab)**:
    -   **Folder**: Select the main folder containing your video files.
    -   **Cache Folder**: Specify a directory for storing cached thumbnails. Defaults to `vtm_cache_default` in the current working directory if left empty.
    -   Adjust thumbnail parameters (count, width, quality), filtering (min size/duration, excluded words/patterns), processing (concurrent videos), and distribution settings.
3.  **Start Processing**:
    -   Click the "Start" button.
    -   The application will first scan the folder for videos (this happens in the background).
    -   Then, it will generate thumbnails for new or modified videos, utilizing CUDA if available and configured.
4.  **Manage Videos (Output Tab)**:
    -   View video entries with their thumbnails.
    -   Select/deselect videos.
    -   Delete selected or unselected videos (files and their cache). This can be done even while other videos are being processed, with a confirmation warning.
    -   Sort the video list.
    -   Jump to specific videos.
5.  **Monitor (Process Tab & Input Tab)**:
    -   The "Process" tab shows FFmpeg commands and live thumbnail previews. It also logs overall scan and generation times.
    -   The "Input" tab shows the main progress bar and ETA.

## Configuration (`config.json`)
The application automatically saves your settings from the GUI into `config.json` in the project's root directory.

-   `cache_dir`: Directory for thumbnail cache.
-   `default_folder`: Last used video input folder.
-   `thumbnails_per_video`: Number of thumbnails per video.
-   `thumbnails_per_column`: Number of thumbnail columns in the output display.
-   `thumbnail_width`: Width of each thumbnail image.
-   `thumbnail_quality`: FFmpeg quality for JPEGs (1-31, lower is better).
-   `concurrent_videos`: Number of videos to process in parallel for thumbnail generation.
-   `zoom_factor`: Magnification for Ctrl+Hover thumbnail preview.
-   `min_size_mb`, `min_duration_seconds`: Filters for video scanning.
-   `use_peak_concentration`, `thumbnail_peak_pos`, `thumbnail_concentration`, `thumbnail_distribution`: Settings for thumbnail timestamp distribution.
-   `excluded_words`, `excluded_words_regex`, `excluded_words_match_full_path`: Filters for excluding files/folders during scanning.

## Thumbnail Generation Process
The application uses a series of FFmpeg commands to robustly generate thumbnails, attempting more optimized methods first and falling back if they fail:
1.  **CUDA HWAccel (various attempts)**: Tries different combinations of CUDA hardware acceleration flags and pixel format conversions for speed.
2.  **CPU Fallback**: If CUDA attempts fail, it reverts to CPU-based decoding and scaling, which is generally more compatible.
3.  **Placeholder**: If all FFmpeg attempts for a specific thumbnail fail, a gray placeholder image is generated and saved.
Detailed FFmpeg commands and errors can be found in `debug.log`.

## Screenshots
![Example GIF showing application usage](contents/example/vtm_example.gif)

## Troubleshooting
-   **FFmpeg Not Found**: Ensure FFmpeg is installed and its directory is in your system's PATH. Verify by typing `ffmpeg -version` in a command prompt/terminal.
-   **No Thumbnails Generated / Errors**: Check `debug.log` in the application's root directory for detailed FFmpeg errors or other issues. Ensure videos are accessible and not corrupted.
-   **CUDA Not Used**: Confirm your FFmpeg build includes CUDA support (`ffmpeg -hwaccels`). Ensure NVIDIA drivers are up-to-date and your GPU is CUDA-capable.
-   **Slow Processing**:
    -   If you have an NVIDIA GPU, ensure CUDA is working.
    -   Reduce "Concurrent Videos" in the GUI settings.
    -   The initial scan of a very large number of files can take time due to FFmpeg calls for duration/metadata for each potential video file.
-   **GUI Issues / Freezing (Improved)**: While significantly improved with background processing, operations on extremely large datasets might still show some UI lag during batched updates. Further optimizations are ongoing.

For persistent issues, please open an issue on GitHub, providing details from `debug.log`, your OS, Python version, FFmpeg version, and steps to reproduce the problem.

## Contributing
Contributions are welcome! Please follow standard Git practices: fork, branch, commit, and pull request. Ensure your changes are well-documented and tested if possible.

## Support the Project
If you find this tool useful, please consider supporting its development:

-   **GitHub Sponsors**: [kerasty2024](https://github.com/sponsors/kerasty2024)
-   **Buy Me a Coffee**: [kerasty](https://www.buymeacoffee.com/kerasty)

### Cryptocurrency Donations
Support the project by sending cryptocurrency to the following addresses:

| Cryptocurrency | Address                                    | QR Code                                          |
| :------------- | :----------------------------------------- | :----------------------------------------------- |
| Bitcoin (BTC)  | `bc1qn72yvftnuh7jgjnn9x848pzhhywasxmqt5c7wp` | ![BTC QR Code](contents/crypto/BTC_QR.jpg)       |
| Ethereum (ETH) | `0x2175Ed9c75C14F113ab9cEaDc1890b2f87f40e78` | ![ETH QR Code](contents/crypto/ETH_QR.jpg)       |
| Solana (SOL)   | `6Hc7erZqgreTVwCsTtNvsyzigN2oHJ4EgNGaLWtRWJ69` | ![Solana QR Code](contents/crypto/Solana_QR.jpg) |

Your contributions help fund development, server costs, and future enhancements. Thank you!

## License
This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

---

<!-- Japanese section -->
<a id="ビデオサムネイルマネージャー-ja"></a>
## ビデオサムネイルマネージャー (日本語)

![スクリーンショット](contents/example/screenshot_output_tab_1.jpg)

FFmpeg と **PyQt6** ベースのグラフィカルユーザーインターフェース（GUI）を使用した Python アプリケーションで、ビデオとサムネイルを管理します。このツールは、ビデオファイルを効率的に処理し、サムネイルを生成し、ビデオコレクションを管理するためのユーザーフレンドリーなインターフェースを提供することを目的としています。

## 機能
- **高度なサムネイル生成**: FFmpeg がサポートするあらゆる形式のビデオに対し、ビデオごとに複数のサムネイルを生成します。
- **GPU アクセラレーション (CUDA)**: CUDA ハードウェアアクセラレーションを利用してサムネイル生成を高速化し、問題のあるビデオや非対応ハードウェアの場合は CPU 処理への堅牢なフォールバック機構を備えています。
- **インテリジェントなキャッシュ**: 生成されたサムネイルと関連メタデータをキャッシュします。生成パラメータ（サムネイル数、幅、品質、分布設定など）が変更されるとキャッシュは無効化され、常に最新のプレビューを保証します。
- **応答性の高い PyQt6 GUI**:
    - **タブ形式インターフェース**: 入力設定、出力表示、プロセス監視のための独立したタブ。
    - **出力タブ**:
        - 生成されたサムネイルをスクロール可能なグリッドに表示。
        - チェックボックスによる複数ビデオの選択。
        - アクション: 選択したビデオ（およびそのキャッシュ）の削除、未選択ビデオの削除、全選択解除。これらの操作はサムネイル生成中でも可能です。
        - ソート: 元の順序、名前、サイズ、再生時間、更新日時でビデオをソート。
        - ジャンプ: 現在の表示番号またはファイル名/パス内のキーワード検索で特定のビデオにジャンプ。
        - ズーム: Ctrl キーを押しながらサムネイルにマウスオーバーすると拡大プレビューを表示。
        - パス表示: フルパスとファイル名のみの表示を切り替え。
        - スクロール速度調整可能。
- **カスタマイズ可能な処理設定**:
    - **入力タブ**: サムネイル生成（ビデオごとの枚数、幅、品質）、ビデオフィルタリング（最小再生時間、最小サイズ）、処理（同時実行ビデオ数）に関する広範な設定。
    - **サムネイル分布**: ビデオのタイムラインからサムネイルをどのように選択するかを指定:
        - **均等 (Uniform)**: 等間隔のサムネイル。
        - **ピーク集中 (Peak-Concentration)**: （三角分布または正規分布を使用）ビデオ内の特定ポイント周辺にサムネイル生成を集中させ、ピーク位置と集中度を調整可能。
    - **ビデオスキャンフィルター**:
        - 最小ファイルサイズと最小再生時間に基づいてビデオを除外。
        - 特定のキーワードを含む、または正規表現に一致するファイル/フォルダを除外。フルパスまたは名前のみに対する一致オプションあり。
- **バックグラウンド処理**: サムネイルのスキャンと生成はバックグラウンドのワーカースレッドで実行され、GUI の応答性を維持します。
- **リアルタイムフィードバック**:
    - **プログレスバー & ETA**: バッチ全体の進捗と推定残り時間。
    - **プロセスタブ**: 実行中の FFmpeg コマンドを表示し、現在生成中のサムネイルのライブプレビューを表示。スキャン時間と総サムネイル生成時間もログに記録。
- **設定管理**: 設定は `config.json` に保存され、起動時に読み込まれます。GUI での変更はこのファイルに反映されます。
- **エラー処理とロギング**: `debug.log` への詳細なログ記録と、複数のフォールバック戦略を備えた堅牢な FFmpeg コマンド実行。
- **クロスプラットフォーム**: Windows, macOS, Linux で動作するように設計されています（Python, PyQt6, FFmpeg が利用可能な環境）。
- **スポンサーシップと暗号通貨サポート**: GUI に表示される QR コードやアドレスを通じて、GitHub Sponsors, Buy Me a Coffee, または暗号通貨でプロジェクトをサポートするオプション。

## 要件
- **Python**: 3.8 以上。
- **FFmpeg**: インストールされ、システムの PATH を通じてアクセス可能であること。
    - [FFmpeg.org](https://ffmpeg.org/) からダウンロードするか、パッケージマネージャ（例: `apt install ffmpeg`, `brew install ffmpeg`）経由でインストール。
    - GPU アクセラレーションには、CUDA サポート付きの FFmpeg ビルドが必要です（NVIDIA GPU とドライバも必要）。
- **Python パッケージ**: `requirements.txt` から依存関係をインストール:
    ```bash
    pip install -r requirements.txt
    ```
    主な依存関係:
    - `PyQt6` (GUI 用)
    - `Pillow` (画像操作用)
    - `loguru` (ロギング用)
    - `numpy` (サムネイル分布計算用)
- **ハードウェア (CUDA 用)**: CUDA 対応の NVIDIA GPU と互換性のあるドライバ（オプションですが、パフォーマンス向上のために強く推奨）。

## インストール
Windows ユーザーは、プロジェクトのリリースパージからビルド済みの実行ファイルを入手できる場合があります。ソースから実行する場合:

1.  **リポジトリをクローン**:
    ```bash
    git clone https://github.com/kerasty2024/video_thumbnail_manager.git
    cd video_thumbnail_manager
    ```
2.  **仮想環境のセットアップ (推奨)**:
    ```bash
    python -m venv .venv
    # アクティベート:
    # Windows: .venv\Scripts\activate
    # macOS/Linux: source .venv/bin/activate
    ```
3.  **Python 依存関係のインストール**:
    ```bash
    pip install -r requirements.txt
    ```
4.  **FFmpeg のインストール**:
    -   システムの PATH に追加されていることを確認してください。
    -   `ffmpeg -version` で確認。
5.  **FFmpeg の CUDA サポート確認 (オプション)**:
    -   ターミナルで `ffmpeg -hwaccels` を実行。CUDA サポート付きで FFmpeg がコンパイルされていれば `cuda` がリストされます。
    -   NVIDIA ドライバが最新であることを確認してください。

## 使用方法
1.  **アプリケーションの実行**:
    ```bash
    python src/main.py
    ```
2.  **設定の構成 (入力タブ)**:
    -   **フォルダ**: ビデオファイルが含まれるメインフォルダを選択します。
    -   **キャッシュフォルダ**: 生成されたサムネイルを保存するディレクトリを指定します。空の場合、カレントワーキングディレクトリに `vtm_cache_default` が作成されます。
    -   サムネイルパラメータ（枚数、幅、品質）、フィルタリング（最小サイズ/再生時間、除外キーワード/パターン）、処理（同時実行ビデオ数）、分布設定を調整します。
3.  **処理の開始**:
    -   「Start」ボタンをクリックします。
    -   アプリケーションはまずフォルダ内のビデオをスキャンします（バックグラウンドで実行）。
    -   その後、新規または変更されたビデオのサムネイルを生成します。CUDA が利用可能で設定されていれば使用されます。
4.  **ビデオの管理 (出力タブ)**:
    -   サムネイル付きのビデオエントリを表示します。
    -   ビデオを選択/選択解除します。
    -   選択したビデオまたは未選択のビデオを削除します（ファイルとキャッシュ）。この操作は他のビデオの処理中でも可能です（確認警告が表示されます）。
    -   ビデオリストをソートします。
    -   特定のビデオにジャンプします。
5.  **監視 (プロセスタブ & 入力タブ)**:
    -   「プロセス」タブには FFmpeg コマンドとライブサムネイルプレビューが表示されます。また、全体のスキャン時間と生成時間も記録されます。
    -   「入力」タブにはメインのプログレスバーと ETA が表示されます。

## 設定 (`config.json`)
アプリケーションは GUI からの設定をプロジェクトのルートディレクトリにある `config.json` ファイルに自動的に保存します。

-   `cache_dir`: サムネイルキャッシュのディレクトリ。
-   `default_folder`: 最後に使用されたビデオ入力フォルダ。
-   `thumbnails_per_video`: ビデオごとのサムネイル数。
-   `thumbnails_per_column`: 出力表示でのサムネイル列数。
-   `thumbnail_width`: 各サムネイル画像の幅。
-   `thumbnail_quality`: JPEG 用の FFmpeg 品質（1-31、低いほど高品質）。
-   `concurrent_videos`: サムネイル生成のために並列処理するビデオの数。
-   `zoom_factor`: Ctrl+ホバー時のサムネイルプレビューの倍率。
-   `min_size_mb`, `min_duration_seconds`: ビデオスキャン時のフィルター。
-   `use_peak_concentration`, `thumbnail_peak_pos`, `thumbnail_concentration`, `thumbnail_distribution`: サムネイルタイムスタンプ分布の設定。
-   `excluded_words`, `excluded_words_regex`, `excluded_words_match_full_path`: スキャン時にファイル/フォルダを除外するためのフィルター。

## サムネイル生成プロセス
アプリケーションは、より最適化された方法を最初に試み、失敗した場合にはフォールバックする一連の FFmpeg コマンドを使用して、堅牢にサムネイルを生成します。
1.  **CUDA HWAccel (様々な試行)**: CUDA ハードウェアアクセラレーションフラグとピクセルフォーマット変換の様々な組み合わせを試行し、速度を追求します。
2.  **CPU フォールバック**: CUDA の試行が失敗した場合、CPU ベースのデコードとスケーリングに切り替えます。これは一般的に互換性が高いです。
3.  **プレースホルダ**: 特定のサムネイルに対する全ての FFmpeg の試行が失敗した場合、灰色のプレースホルダイメージが生成・保存されます。
詳細な FFmpeg コマンドとエラーは `debug.log` で確認できます。

## スクリーンショット
![使用例GIF](contents/example/vtm_example.gif)

## トラブルシューティング
-   **FFmpeg が見つからない**: FFmpeg がインストールされ、そのディレクトリがシステムの PATH に追加されていることを確認してください。コマンドプロンプト/ターミナルで `ffmpeg -version` と入力して確認します。
-   **サムネイルが生成されない / エラー**: アプリケーションのルートディレクトリにある `debug.log` で詳細な FFmpeg エラーやその他の問題を確認してください。ビデオファイルがアクセス可能で破損していないことを確認してください。
-   **CUDA が使用されない**: FFmpeg ビルドに CUDA サポートが含まれていることを確認してください（`ffmpeg -hwaccels`）。NVIDIA ドライバが最新であり、GPU が CUDA 対応であることを確認してください。
-   **処理が遅い**:
    -   NVIDIA GPU をお持ちの場合は、CUDA が機能していることを確認してください。
    -   GUI 設定で「同時実行ビデオ数」を減らしてください。
    -   非常に多数のファイルを初めてスキャンする場合、各潜在的ビデオファイルの再生時間/メタデータ取得のための FFmpeg 呼び出しにより時間がかかることがあります。
-   **GUI の問題 / フリーズ (改善済み)**: バックグラウンド処理により大幅に改善されましたが、非常に大規模なデータセットに対する操作では、バッチ更新中に若干のUIの遅延が見られる可能性があります。さらなる最適化は継続中です。

解決しない問題については、GitHub の Issue に `debug.log` の詳細、OS、Python バージョン、FFmpeg バージョン、問題再現手順を添えて報告してください。

## 貢献
貢献を歓迎します！標準的な Git の慣習に従ってください: フォーク、ブランチ作成、コミット、プルリクエスト。変更点が十分に文書化され、可能であればテストされていることを確認してください。

## プロジェクト支援
このツールが役立つと思われたら、開発のサポートをご検討ください:

-   **GitHub Sponsors**: [kerasty2024](https://github.com/sponsors/kerasty2024)
-   **Buy Me a Coffee**: [kerasty](https://www.buymeacoffee.com/kerasty)

### 暗号通貨による寄付
以下のアドレスに暗号通貨を送ることでプロジェクトを支援できます:

| 暗号通貨       | アドレス                                    | QR コード                                          |
| :------------- | :----------------------------------------- | :----------------------------------------------- |
| ビットコイン (BTC)  | `bc1qn72yvftnuh7jgjnn9x848pzhhywasxmqt5c7wp` | ![BTC QR コード](contents/crypto/BTC_QR.jpg)       |
| イーサリアム (ETH) | `0x2175Ed9c75C14F113ab9cEaDc1890b2f87f40e78` | ![ETH QR コード](contents/crypto/ETH_QR.jpg)       |
| ソラナ (SOL)   | `6Hc7erZqgreTVwCsTtNvsyzigN2oHJ4EgNGaLWtRWJ69` | ![Solana QR コード](contents/crypto/Solana_QR.jpg) |

あなたの貢献が開発、サーバー費用、将来の機能強化の資金となります。ありがとうございます！

## ライセンス
このプロジェクトは MITライセンス の下でライセンスされています - 詳細は [LICENSE](LICENSE) ファイルをご覧ください。

---

<!-- Chinese section -->
<a id="视频缩略图管理器-zh"></a>
## 视频缩略图管理器 (简体中文)

![截图](contents/example/screenshot_output_tab_1.jpg)

一款使用 FFmpeg 和基于 **PyQt6** 的图形用户界面（GUI） Python 应用程序，用于管理视频和缩略图。该工具旨在高效处理视频文件、生成缩略图，并提供用户友好的界面来管理视频集合。

## 功能
- **高级缩略图生成**: 为 FFmpeg 支持的任何格式视频，每个视频生成多个缩略图。
- **GPU 加速 (CUDA)**: 利用 CUDA 硬件加速以加快缩略图生成速度，并为有问题的视频或不支持的硬件提供强大的 CPU 处理回退机制。
- **智能缓存**: 缓存生成的缩略图及相关元数据。如果生成参数（如缩略图数量、宽度、质量、分布设置）发生更改，缓存将失效，以确保预览始终是最新状态。
- **响应式 PyQt6 GUI**:
    - **选项卡式界面**: 用于输入设置、输出显示和过程监控的独立选项卡。
    - **输出选项卡**:
        - 在可滚动的网格中显示生成的缩略图。
        - 通过复选框选择多个视频。
        - 操作：删除选定的视频（及其缓存）、删除未选中的视频、清除所有选择。即使在缩略图生成过程中，这些操作也可用。
        - 排序：按原始顺序、名称、大小、时长或修改日期对视频进行排序。
        - 跳转：通过当前显示编号跳转到特定视频，或通过文件名/路径中的关键字搜索。
        - 缩放：按住 Ctrl 键并将鼠标悬停在缩略图上可查看放大预览。
        - 路径显示：切换显示完整路径或仅显示文件名。
        - 可调滚动速度。
- **可配置处理**:
    - **输入选项卡**: 关于缩略图生成（每个视频的数量、宽度、质量）、视频过滤（最小时长、最小大小）和处理（并发视频数）的广泛设置。
    - **缩略图分布**: 选择如何从视频的时间轴中选取缩略图：
        - **均匀 (Uniform)**: 均匀间隔的缩略图。
        - **峰值集中 (Peak-Concentration)**: （使用三角或正态分布）将缩略图生成集中在视频中的特定点附近，可调整峰值位置和集中度。
    - **视频扫描过滤器**:
        - 根据最小文件大小和最小时长排除视频。
        - 排除包含特定关键字或匹配正则表达式的文件/文件夹。可选择针对完整路径或仅名称进行匹配。
- **后台处理**: 缩略图扫描和生成在后台工作线程中运行，保持 GUI 的响应性。
- **实时反馈**:
    - **进度条 & ETA**: 显示批处理的总体进度和预计剩余时间。
    - **进程选项卡**: 显示正在执行的 FFmpeg 命令，并实时预览当前正在生成的缩略图。还会记录扫描持续时间和总缩略图生成时间。
- **配置管理**: 设置保存在 `config.json` 中，并在启动时加载。GUI 中的更改会更新此文件。
- **错误处理与日志记录**: 详细日志记录到 `debug.log`，以及具有多种回退策略的强大 FFmpeg 命令执行。
- **跨平台**: 设计用于在 Windows、macOS 和 Linux上运行（需要 Python、PyQt6 和 FFmpeg 环境）。
- **赞助与加密货币支持**: 可通过 GUI 中显示的二维码和地址，选择通过 GitHub Sponsors、Buy Me a Coffee 或加密货币捐赠来支持项目。

## 要求
- **Python**: 3.8 或更高版本。
- **FFmpeg**: 必须已安装并通过系统 PATH 访问。
    - 从 [FFmpeg.org](https://ffmpeg.org/) 下载或通过包管理器安装（例如 `apt install ffmpeg`, `brew install ffmpeg`）。
    - 若要使用 GPU 加速，需要支持 CUDA 的 FFmpeg 版本（以及 NVIDIA GPU 和驱动程序）。
- **Python 包**: 从 `requirements.txt` 安装依赖项：
    ```bash
    pip install -r requirements.txt
    ```
    主要依赖项包括：
    - `PyQt6` (用于 GUI)
    - `Pillow` (用于图像处理)
    - `loguru` (用于日志记录)
    - `numpy` (用于缩略图分布计算)
- **硬件 (CUDA)**: 支持 CUDA 的 NVIDIA GPU 及兼容驱动程序（可选，但强烈建议以获得更佳性能）。

## 安装
Windows 用户通常可以在项目的 Release 页面找到预编译的可执行文件。若要从源代码运行：

1.  **克隆仓库**:
    ```bash
    git clone https://github.com/kerasty2024/video_thumbnail_manager.git
    cd video_thumbnail_manager
    ```
2.  **设置虚拟环境 (推荐)**:
    ```bash
    python -m venv .venv
    # 激活:
    # Windows: .venv\Scripts\activate
    # macOS/Linux: source .venv/bin/activate
    ```
3.  **安装 Python 依赖**:
    ```bash
    pip install -r requirements.txt
    ```
4.  **安装 FFmpeg**:
    -   确保其在系统 PATH中。
    -   通过 `ffmpeg -version` 验证。
5.  **验证 FFmpeg 中的 CUDA 支持 (可选)**:
    -   在终端运行 `ffmpeg -hwaccels`。如果 FFmpeg 编译时支持 CUDA，列表中应包含 `cuda`。
    -   确保 NVIDIA 驱动程序是最新版本。

## 使用方法
1.  **运行应用程序**:
    ```bash
    python src/main.py
    ```
2.  **配置设置 (输入选项卡)**:
    -   **文件夹**: 选择包含视频文件的主文件夹。
    -   **缓存文件夹**: 指定用于存储缓存缩略图的目录。如果留空，则默认为当前工作目录下的 `vtm_cache_default`。
    -   调整缩略图参数（数量、宽度、质量）、过滤（最小大小/时长、排除词/模式）、处理（并发视频数）和分布设置。
3.  **开始处理**:
    -   点击“Start”按钮。
    -   应用程序将首先扫描文件夹中的视频（在后台进行）。
    -   然后，它将为新的或已修改的视频生成缩略图，如果可用且已配置，则使用 CUDA。
4.  **管理视频 (输出选项卡)**:
    -   查看带有缩略图的视频条目。
    -   选择/取消选择视频。
    -   删除选定或未选定的视频（文件及其缓存）。即使在处理其他视频时也可以执行此操作（会有确认警告）。
    -   对视频列表进行排序。
    -   跳转到特定视频。
5.  **监控 (进程选项卡 & 输入选项卡)**:
    -   “进程”选项卡显示 FFmpeg 命令和实时缩略图预览。它还记录总扫描时间和生成时间。
    -   “输入”选项卡显示主进度条和 ETA。

## 配置 (`config.json`)
应用程序会自动将您在 GUI 中所做的设置保存到项目根目录下的 `config.json` 文件中。

-   `cache_dir`: 缩略图缓存目录。
-   `default_folder`: 上次使用的视频输入文件夹。
-   `thumbnails_per_video`: 每个视频的缩略图数量。
-   `thumbnails_per_column`: 输出显示中的缩略图列数。
-   `thumbnail_width`: 每个缩略图图像的宽度。
-   `thumbnail_quality`: JPEG 的 FFmpeg 质量（1-31，越低越好）。
-   `concurrent_videos`: 并行处理缩略图生成的视频数量。
-   `zoom_factor`: Ctrl+鼠标悬停缩略图预览的放大倍数。
-   `min_size_mb`, `min_duration_seconds`: 视频扫描过滤器。
-   `use_peak_concentration`, `thumbnail_peak_pos`, `thumbnail_concentration`, `thumbnail_distribution`: 缩略图时间戳分布设置。
-   `excluded_words`, `excluded_words_regex`, `excluded_words_match_full_path`: 扫描期间排除文件/文件夹的过滤器。

## 缩略图生成过程
该应用程序使用一系列 FFmpeg 命令来稳健地生成缩略图，首先尝试更优化的方法，如果失败则回退：
1.  **CUDA HWAccel (多种尝试)**: 尝试 CUDA 硬件加速标志和像素格式转换的不同组合以提高速度。
2.  **CPU 回退**: 如果 CUDA 尝试失败，则恢复为基于 CPU 的解码和缩放，这通常具有更好的兼容性。
3.  **占位符**: 如果特定缩略图的所有 FFmpeg 尝试均失败，则会生成并保存一个灰色占位符图像。
详细的 FFmpeg 命令和错误可以在 `debug.log` 中找到。

## 屏幕截图
![应用程序使用示例 GIF](contents/example/vtm_example.gif)

## 故障排除
-   **找不到 FFmpeg**: 确保已安装 FFmpeg 并将其目录添加到系统 PATH。在命令提示符/终端中键入 `ffmpeg -version` 进行验证。
-   **未生成缩略图/错误**: 检查应用程序根目录中的 `debug.log` 以获取详细的 FFmpeg 错误或其他问题。确保视频可访问且未损坏。
-   **CUDA 未使用**: 确认您的 FFmpeg 版本包含 CUDA 支持 (`ffmpeg -hwaccels`)。确保 NVIDIA 驱动程序是最新版本并且您的 GPU 支持 CUDA。
-   **处理缓慢**:
    -   如果您有 NVIDIA GPU，请确保 CUDA 正常工作。
    -   在 GUI 设置中减少“并发视频数”。
    -   首次扫描大量文件可能会花费一些时间，因为需要为每个潜在的视频文件调用 FFmpeg 以获取时长/元数据。
-   **GUI 问题/冻结 (已改进)**: 尽管通过后台处理已显著改进，但在处理极大数据集时，批量更新期间仍可能出现一些 UI 延迟。正在进行进一步优化。

对于持续存在的问题，请在 GitHub 上提交 issue，提供 `debug.log` 的详细信息、您的操作系统、Python 版本、FFmpeg 版本以及重现问题的步骤。

## 贡献
欢迎贡献！请遵循标准的 Git 实践：fork、创建分支、提交和发起拉取请求。请确保您的更改有充分的文档记录，并在可能的情况下进行测试。

## 支持项目
如果您觉得这个工具有用，请考虑支持其开发：

-   **GitHub Sponsors**: [kerasty2024](https://github.com/sponsors/kerasty2024)
-   **Buy Me a Coffee**: [kerasty](https://www.buymeacoffee.com/kerasty)

### 加密货币捐赠
通过向以下地址发送加密货币来支持本项目：

| 加密货币       | 地址                                                       | 二维码                                            |
| :------------- | :--------------------------------------------------------- | :----------------------------------------------- |
| 比特币 (BTC)   | `bc1qn72yvftnuh7jgjnn9x848pzhhywasxmqt5c7wp`                | ![BTC 二维码](contents/crypto/BTC_QR.jpg)         |
| 以太坊 (ETH)   | `0x2175Ed9c75C14F113ab9cEaDc1890b2f87f40e78`                | ![ETH 二维码](contents/crypto/ETH_QR.jpg)         |
| Solana (SOL)   | `6Hc7erZqgreTVwCsTtNvsyzigN2oHJ4EgNGaLWtRWJ69`                | ![Solana 二维码](contents/crypto/Solana_QR.jpg)   |

您的贡献有助于项目的开发、服务器成本以及未来的功能增强。谢谢！

## 许可证
本项目采用 MIT 许可证 - 详情请参阅 [LICENSE](LICENSE) 文件。