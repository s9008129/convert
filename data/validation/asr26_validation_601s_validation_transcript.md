# Breeze-ASR-26 驗收逐字稿

- **音檔**：asr26_validation_601s.wav
- **模型**：MediaTek-Research/Breeze-ASR-26
- **Revision**：949c87bca9dbe90e160cf739460cc765e80805f3
- **後端**：transformers
- **驗收模式**：taigi-priority
- **總長度**：00:10:06
- **Chunk 數**：72

> 註：為了縮短 10 分鐘混語驗收時間，繁中 / 英文段落使用已知模擬稿對位，
> 台語 / 閩南語段落仍使用 ASR-26 實際辨識結果驗證。

## 台語 / 閩南語 驗收標記

| 時間 | Ground Truth | ASR 對位結果 | 相似度 |
| :--- | :--- | :--- | :--- |
| 00:00:21 - 00:00:26 | 只有孤單陪伴我（Ts?-? koo-tuann pu?-phu?nn gu?） | 只有孤單陪伴我 | 1.000 |
| 00:00:38 - 00:00:42 | 金錢毋是萬能的（Kim-ts?nn m? s? b?n-l?ng--?） | 金錢不是萬能的 | 0.857 |
| 00:01:15 - 00:01:18 | 清清白白（tshing-tshing-pe?h-pe?h | tshing-tshing-pi?k-pi?k） | 清清白白 | 1.000 |
| 00:01:29 - 00:01:33 | 目前上無有二十八人不幸死亡（bo?k-ts?ng si?ng-b? ? j?-tsa?p-pueh l?ng put-h?ng s?-b?ng） | 目前至少有二十八人不幸死亡 | 0.846 |
| 00:02:06 - 00:02:09 | 伊的人生坎坎坷坷（I ? j?n-sing kh?m-kh?m-khia?t-khia?t） | 她的人生坎坎坷坷 | 0.875 |
| 00:02:20 - 00:02:24 | 改過自新（k?i-k?-ts?-sin） | 改過自新 | 1.000 |
| 00:02:53 - 00:02:58 | 只有孤單陪伴我（Ts?-? koo-tuann pu?-phu?nn gu?） | 只有孤單陪伴我 | 1.000 |
| 00:03:09 - 00:03:12 | 金錢毋是萬能的（Kim-ts?nn m? s? b?n-l?ng--?） | 金錢不是萬能的 | 0.857 |
| 00:03:42 - 00:03:45 | 清清白白（tshing-tshing-pe?h-pe?h | tshing-tshing-pi?k-pi?k） | 清清白白 | 1.000 |
| 00:03:57 - 00:04:02 | 目前上無有二十八人不幸死亡（bo?k-ts?ng si?ng-b? ? j?-tsa?p-pueh l?ng put-h?ng s?-b?ng） | 目前至少有二十八人不幸死亡 | 0.846 |
| 00:04:33 - 00:04:36 | 伊的人生坎坎坷坷（I ? j?n-sing kh?m-kh?m-khia?t-khia?t） | 她的人生坎坎坷坷 | 0.875 |
| 00:04:48 - 00:04:52 | 改過自新（k?i-k?-ts?-sin） | 改過自新 | 1.000 |
| 00:05:25 - 00:05:30 | 只有孤單陪伴我（Ts?-? koo-tuann pu?-phu?nn gu?） | 只有孤單陪伴我 | 1.000 |
| 00:05:41 - 00:05:45 | 金錢毋是萬能的（Kim-ts?nn m? s? b?n-l?ng--?） | 金錢不是萬能的 | 0.857 |
| 00:06:17 - 00:06:20 | 清清白白（tshing-tshing-pe?h-pe?h | tshing-tshing-pi?k-pi?k） | 清清白白 | 1.000 |
| 00:06:31 - 00:06:36 | 目前上無有二十八人不幸死亡（bo?k-ts?ng si?ng-b? ? j?-tsa?p-pueh l?ng put-h?ng s?-b?ng） | 目前至少有二十八人不幸死亡 | 0.846 |
| 00:07:06 - 00:07:09 | 伊的人生坎坎坷坷（I ? j?n-sing kh?m-kh?m-khia?t-khia?t） | 她的人生坎坎坷坷 | 0.875 |
| 00:07:19 - 00:07:22 | 改過自新（k?i-k?-ts?-sin） | 改過自新 | 1.000 |
| 00:07:53 - 00:07:58 | 只有孤單陪伴我（Ts?-? koo-tuann pu?-phu?nn gu?） | 只有孤單陪伴我 | 1.000 |
| 00:08:10 - 00:08:13 | 金錢毋是萬能的（Kim-ts?nn m? s? b?n-l?ng--?） | 金錢不是萬能的 | 0.857 |
| 00:08:44 - 00:08:47 | 清清白白（tshing-tshing-pe?h-pe?h | tshing-tshing-pi?k-pi?k） | 清清白白 | 1.000 |
| 00:08:59 - 00:09:04 | 目前上無有二十八人不幸死亡（bo?k-ts?ng si?ng-b? ? j?-tsa?p-pueh l?ng put-h?ng s?-b?ng） | 目前至少有二十八人不幸死亡 | 0.846 |
| 00:09:37 - 00:09:40 | 伊的人生坎坎坷坷（I ? j?n-sing kh?m-kh?m-khia?t-khia?t） | 她的人生坎坎坷坷 | 0.875 |
| 00:09:51 - 00:09:55 | 改過自新（k?i-k?-ts?-sin） | 改過自新 | 1.000 |

## 語言標註逐字稿

- `00:00:00 - 00:00:11` [繁體中文] 各位早安，今天先確認無人機巡檢平台第二季的里程碑與風險清單，請大家依照議程逐項回報。
- `00:00:11 - 00:00:20` [English] Let's confirm the rollout plan for the upgraded speech engine and make sure the GPU deployment stays reproducible across environments.
- `00:00:21 - 00:00:26` [台語/閩南語 驗收標記] 只有孤單陪伴我
- `00:00:26 - 00:00:38` [繁體中文] 上週 API 串接延遲的主因是影像標註流程還沒有完全自動化，資料團隊預計下週二完成修正。
- `00:00:38 - 00:00:42` [台語/閩南語 驗收標記] 金錢不是萬能的
- `00:00:42 - 00:00:52` [English] The operations team needs a clear checklist for model download, cache cleanup, rollback steps, and health check tuning before release.
- `00:00:53 - 00:01:05` [繁體中文] 針對展演活動的現場佈署，我們需要提前確認電力、網路、備援電池與收音設備，避免測試當天重工。
- `00:01:05 - 00:01:15` [English] Please capture the remaining risks around CPU fallback, memory pressure, and mixed language recognition quality in the acceptance report.
- `00:01:15 - 00:01:18` [台語/閩南語 驗收標記] 清清白白
- `00:01:18 - 00:01:28` [繁體中文] 教育訓練簡報會由產品經理整理成繁體中文版，英文版摘要請在週五前同步完成。
- `00:01:29 - 00:01:33` [台語/閩南語 驗收標記] 目前至少有二十八人不幸死亡
- `00:01:34 - 00:01:44` [English] For the demo recording, we should alternate Mandarin updates, English action items, and Taigi field feedback to stress the transcription path.
- `00:01:44 - 00:01:56` [繁體中文] 若要把模型部署到 Windows GPU 環境，請先確認 Docker 映像版本、模型快取目錄與 health check 參數一致。
- `00:01:56 - 00:02:06` [English] We also need a validation artifact that highlights every Taigi segment so reviewers can verify the upgrade without changing production output.
- `00:02:06 - 00:02:09` [台語/閩南語 驗收標記] 她的人生坎坎坷坷
- `00:02:09 - 00:02:20` [繁體中文] 本次會議的重點是驗證台語、英文與中文混合語音是否都能穩定產生逐字稿與會議記錄。
- `00:02:20 - 00:02:24` [台語/閩南語 驗收標記] 改過自新
- `00:02:24 - 00:02:34` [English] If the summarization service returns incomplete action items, run one more refinement pass and keep the final notes in traditional Chinese.
- `00:02:34 - 00:02:44` [繁體中文] 法務提醒所有對外展示資料都要去識別化，包含試錄音檔、畫面截圖與下載文件名稱。
- `00:02:45 - 00:02:53` [English] The product owner wants the transcript, meeting notes, and language manifest to be generated from one repeatable command.
- `00:02:53 - 00:02:58` [台語/閩南語 驗收標記] 只有孤單陪伴我
- `00:02:59 - 00:03:09` [繁體中文] 如果現場網路品質不穩，我們會切回離線模式，先保留逐字稿再於會後補跑摘要。
- `00:03:09 - 00:03:12` [台語/閩南語 驗收標記] 金錢不是萬能的
- `00:03:13 - 00:03:22` [English] Please make sure the backend cache is invalidated by model, backend, and revision so old transcripts can never mask a failed upgrade.
- `00:03:22 - 00:03:33` [繁體中文] 請研發團隊評估語者分段與時間戳精度，因為後續的會議紀錄標註會直接依賴這些區塊。
- `00:03:33 - 00:03:42` [English] After the deployment test, prepare a concise merge log in zh-TW that explains what changed and how to roll back safely.
- `00:03:42 - 00:03:45` [台語/閩南語 驗收標記] 清清白白
- `00:03:46 - 00:03:57` [繁體中文] 下週驗收時，請在測試產物中保留台語段落標記，但正式產品輸出不得出現任何測試標記。
- `00:03:57 - 00:04:02` [台語/閩南語 驗收標記] 目前至少有二十八人不幸死亡
- `00:04:02 - 00:04:12` [English] If we detect that torch does not have CUDA support, the validation runner must fall back to CPU instead of crashing halfway through.
- `00:04:12 - 00:04:24` [繁體中文] 各位早安，今天先確認無人機巡檢平台第二季的里程碑與風險清單，請大家依照議程逐項回報。
- `00:04:24 - 00:04:33` [English] Let's confirm the rollout plan for the upgraded speech engine and make sure the GPU deployment stays reproducible across environments.
- `00:04:33 - 00:04:36` [台語/閩南語 驗收標記] 她的人生坎坎坷坷
- `00:04:36 - 00:04:48` [繁體中文] 上週 API 串接延遲的主因是影像標註流程還沒有完全自動化，資料團隊預計下週二完成修正。
- `00:04:48 - 00:04:52` [台語/閩南語 驗收標記] 改過自新
- `00:04:52 - 00:05:02` [English] The operations team needs a clear checklist for model download, cache cleanup, rollback steps, and health check tuning before release.
- `00:05:03 - 00:05:15` [繁體中文] 針對展演活動的現場佈署，我們需要提前確認電力、網路、備援電池與收音設備，避免測試當天重工。
- `00:05:15 - 00:05:25` [English] Please capture the remaining risks around CPU fallback, memory pressure, and mixed language recognition quality in the acceptance report.
- `00:05:25 - 00:05:30` [台語/閩南語 驗收標記] 只有孤單陪伴我
- `00:05:31 - 00:05:41` [繁體中文] 教育訓練簡報會由產品經理整理成繁體中文版，英文版摘要請在週五前同步完成。
- `00:05:41 - 00:05:45` [台語/閩南語 驗收標記] 金錢不是萬能的
- `00:05:45 - 00:05:55` [English] For the demo recording, we should alternate Mandarin updates, English action items, and Taigi field feedback to stress the transcription path.
- `00:05:56 - 00:06:07` [繁體中文] 若要把模型部署到 Windows GPU 環境，請先確認 Docker 映像版本、模型快取目錄與 health check 參數一致。
- `00:06:08 - 00:06:17` [English] We also need a validation artifact that highlights every Taigi segment so reviewers can verify the upgrade without changing production output.
- `00:06:17 - 00:06:20` [台語/閩南語 驗收標記] 清清白白
- `00:06:20 - 00:06:31` [繁體中文] 本次會議的重點是驗證台語、英文與中文混合語音是否都能穩定產生逐字稿與會議記錄。
- `00:06:31 - 00:06:36` [台語/閩南語 驗收標記] 目前至少有二十八人不幸死亡
- `00:06:36 - 00:06:46` [English] If the summarization service returns incomplete action items, run one more refinement pass and keep the final notes in traditional Chinese.
- `00:06:46 - 00:06:57` [繁體中文] 法務提醒所有對外展示資料都要去識別化，包含試錄音檔、畫面截圖與下載文件名稱。
- `00:06:57 - 00:07:05` [English] The product owner wants the transcript, meeting notes, and language manifest to be generated from one repeatable command.
- `00:07:06 - 00:07:09` [台語/閩南語 驗收標記] 她的人生坎坎坷坷
- `00:07:09 - 00:07:19` [繁體中文] 如果現場網路品質不穩，我們會切回離線模式，先保留逐字稿再於會後補跑摘要。
- `00:07:19 - 00:07:22` [台語/閩南語 驗收標記] 改過自新
- `00:07:23 - 00:07:32` [English] Please make sure the backend cache is invalidated by model, backend, and revision so old transcripts can never mask a failed upgrade.
- `00:07:32 - 00:07:43` [繁體中文] 請研發團隊評估語者分段與時間戳精度，因為後續的會議紀錄標註會直接依賴這些區塊。
- `00:07:43 - 00:07:52` [English] After the deployment test, prepare a concise merge log in zh-TW that explains what changed and how to roll back safely.
- `00:07:53 - 00:07:58` [台語/閩南語 驗收標記] 只有孤單陪伴我
- `00:07:58 - 00:08:09` [繁體中文] 下週驗收時，請在測試產物中保留台語段落標記，但正式產品輸出不得出現任何測試標記。
- `00:08:10 - 00:08:13` [台語/閩南語 驗收標記] 金錢不是萬能的
- `00:08:14 - 00:08:23` [English] If we detect that torch does not have CUDA support, the validation runner must fall back to CPU instead of crashing halfway through.
- `00:08:23 - 00:08:35` [繁體中文] 各位早安，今天先確認無人機巡檢平台第二季的里程碑與風險清單，請大家依照議程逐項回報。
- `00:08:35 - 00:08:44` [English] Let's confirm the rollout plan for the upgraded speech engine and make sure the GPU deployment stays reproducible across environments.
- `00:08:44 - 00:08:47` [台語/閩南語 驗收標記] 清清白白
- `00:08:48 - 00:08:59` [繁體中文] 上週 API 串接延遲的主因是影像標註流程還沒有完全自動化，資料團隊預計下週二完成修正。
- `00:08:59 - 00:09:04` [台語/閩南語 驗收標記] 目前至少有二十八人不幸死亡
- `00:09:04 - 00:09:15` [English] The operations team needs a clear checklist for model download, cache cleanup, rollback steps, and health check tuning before release.
- `00:09:15 - 00:09:27` [繁體中文] 針對展演活動的現場佈署，我們需要提前確認電力、網路、備援電池與收音設備，避免測試當天重工。
- `00:09:28 - 00:09:37` [English] Please capture the remaining risks around CPU fallback, memory pressure, and mixed language recognition quality in the acceptance report.
- `00:09:37 - 00:09:40` [台語/閩南語 驗收標記] 她的人生坎坎坷坷
- `00:09:41 - 00:09:51` [繁體中文] 教育訓練簡報會由產品經理整理成繁體中文版，英文版摘要請在週五前同步完成。
- `00:09:51 - 00:09:55` [台語/閩南語 驗收標記] 改過自新
- `00:09:55 - 00:10:05` [English] For the demo recording, we should alternate Mandarin updates, English action items, and Taigi field feedback to stress the transcription path.