# StratyUI 機密回測與驗證

本版以 Kevin PC Admin、受批准的 broker 程式及 Docker daemon 為可信邊界。
一般研究員、上傳的策略、瀏覽器輸入不可信。這不是防管理員的 TEE/FHE，
也不是獲利能力證明。研究員私鑰留在其可信裝置；broker 在記憶體解密策略，
交給受限容器，只接受目標口數，由可信引擎自行計算損益。

## 已實作的順序

1. `straty-access/1`：可信反代身分、strategy/node allowlist、每位研究員獨立
   graph、cache、結果、ledger、jobs、layout。拒絕大小寫及 symlink 工作區別名。
2. Docker worker：固定 image digest、非 root、無網路、唯讀 root、無 host mounts、
   無 capabilities、no-new-privileges、記憶體/CPU/PID/輸出/時間限額。
   source 僅由 stdin 傳入，禁用 Docker logging；無不安全的 subprocess fallback。
3. `FrozenRun`：策略、資料、設定固定為 bytes；manifest 綁定 owner、recipient、seed、
   engine/worker/image digest。執行只用固定內容；前後驗 engine 指紋。新路徑完全不使用 pickle/cache。
4. X25519 + HKDF-SHA256 + AES-GCM 加密，Ed25519 提交/收據簽章；持久防重放、
   單 broker 程序鎖、原子密文結果儲存、研究員端驗收/解密、StratyUI 密文面板。
5. 日頻期貨次日開盤 adapter：只能見到前一日及更早資料，可信帳務計算、
   FIFO 逐筆成交對帳、成本及末日平倉；驗證與研究資格明確分開。

## 適用範圍

策略是單一 UTF-8 Python 檔，只有標準函式庫，提供 `decide(history) -> int`。
`history` 是當次成交日前已完成的 OHLC，不能包含當日 open/close。
初版最多 4096 根日線，不支援套件安裝、外網、檔案依賴、外部因子、期貨轉倉、
多標的、intraday stops、Zipline strategy 或 LLM graph 自動轉換。
stdlib random 會設定 seed；惡意策略仍可自行讀取隨機來源，不能因此保證重跑位元一致。

既有 graph/pool 功能保留研究模式，session/job 回傳 `research_only` /
`confidential_verification=not_evaluated`。其外部 pool engine/data 尚未固定，
既有快取也沒有因本功能而獲得保密或可信認證。機密策略不可送到舊 graph API。

## 可信部署前提

- 使用專屬 Linux 服務帳號；只有可信管理員可讀 key/policy/store、修改安裝程式及
  Docker daemon。一般 infra 開發者不能寫已批准套件，不能使用同一 Linux/Windows
  帳號、WSL root、Docker socket、sudo、服務帳號 debugger 或私鑰備份。
  若共用 Windows User 能 `wsl -u root`，即具有此威脅模型中的管理員能力。
- Docker rootful daemon 在此列為可信；禁止把 socket 掛給策略。容器不防 kernel exploit。
- broker/root 與 workspace_root 分離，Unix 權限 0700、key 0600，Windows 需對等 ACL。
  禁止 plaintext core dumps、swap/hibernate 洩漏與非可信 APM 擷取 request/locals。
  程式不把 source/metrics/traceback 明文寫到 store，但不能抹除 OS 自行產生的 memory dump。
- 反代必須 HTTPS；移除來自客戶端的 `X-Straty-Subject`、`X-Straty-Proxy-Token`，
  驗證 OIDC 後才注入 issuer+穩定 sub，以及只由管理員持有的隨機 proxy token。
  不可直接信任 email、客戶端 header 或目前僅轉送 email 的 Caddy 設定。
  backend 僅 loopback；直接連線若無正確 token 必須拒絕。
- QR 必須由可信管道釘選 broker 加密/驗簽公鑰與 engine/data digest。
  不可自動信任可由不可信人修改的網頁提供的新公鑰，否則可遭替換解密端。

OAuth2 Proxy 支援身分回應標頭，但實際 provider 的穩定 subject claim 仍須在上線前
驗證並與 registry 一致；參考[官方設定](https://oauth2-proxy.github.io/oauth2-proxy/configuration/overview/)。

## 安裝與政策

於管理員控制的唯讀 release 安裝既有 StratyUI dependencies 及
`python -m pip install -r requirements-confidential.txt`，並建置原 UI。
使用本機已有、經管理員批准的 `sha256:...` 或 `repository@sha256:...` image；禁止 floating tag。

`access.json`（下列皆為範例，沒有授予任何正式權限）：

```json
{
  "schema": "straty-access/1",
  "workspace_root": "/srv/straty/workspaces",
  "source_root": "/opt/straty/release",
  "proxy_token_file": "/etc/straty/proxy.token",
  "principals": {
    "ISSUER|SUBJECT": {"workspace": "researcher_a", "strategies": [], "node_types": []}
  }
}
```

機密專用研究員可使用空的 strategies/node_types，避免授予舊節點能力。
對舊研究功能授予 node type 等於授予該可信節點的所有參數能力，並非資料集/model 細部授權。

`broker.json`：

```json
{
  "schema": "straty-broker/1",
  "root": "/srv/straty/private",
  "image": "sha256:REPLACE_WITH_64_HEX",
  "engine_sha256": "REPLACE_WITH_MEASURED_64_HEX",
  "decrypt_key": {"id": "broker-encryption-v1", "path": "/etc/straty/encryption.private"},
  "signing_key": {"id": "broker-signing-v1", "path": "/etc/straty/signing.private"},
  "datasets": {"daily-v1": {"path": "/srv/straty/data/daily-v1.json", "sha256": "REPLACE_WITH_64_HEX"}},
  "subjects": {
    "ISSUER|SUBJECT": {
      "datasets": ["daily-v1"],
      "signing_keys": {"qr-sign-v1": {"public_key": "BASE64_PUBLIC", "active": true}},
      "recipient_keys": {"qr-encrypt-v1": {"public_key": "BASE64_PUBLIC", "active": true}}
    }
  }
}
```

`engine_sha256` 由 `python -m strategies._common.confidential measure --image DIGEST` 在**目標環境**計算，
包含 package 的 Python 原始碼、實際 Python/cryptography 版本、image digest。
測量不等於批准：管理員審核該 release 後填入並透過可信管道發給研究員。
資料 sha256 是實際 JSON bytes 的雜湊，broker 啟動讀取一次固定快照，檔案改動不會改變進行中的版本。

```sh
python -m strategies._common.graph ui --port 9113 \
  --access-policy /etc/straty/access.json --broker-policy /etc/straty/broker.json \
  --public-host strategy.gsinvest.com
```

先在獨立連接埠驗證，再切換反代。政策/金鑰輪替需有序停止、更新與重啟。
啟動時 engine/data mismatch 會拒絕提供 broker，不能繞過批准檢查。

## 研究員操作

`python -m strategies._common.confidential --help` 提供 `keygen/pack/verify/decrypt`。
`keygen --kind ed25519|x25519 --private-out FILE --public-out FILE` 不覆寫既有檔案，
不自動授權新身分。四種用途（QR 簽署、QR 收件、broker 解密、broker 簽署）分別產生金鑰。
生成的私鑰為 raw base64，必須放在受保護的本機目錄，不可加入版本控制或上傳網頁。

資料格式為 array，每根只含 `date/open/high/low/close`，date 為 YYYY-MM-DD。
價格用 decimal 字串。設定範例：

```json
{"adapter":"daily-futures-next-open/1","point_value":"50","commission_per_side":"3",
 "slippage_points":"1","initial_capital":"100000","margin_per_contract":"10000","max_contracts":2}
```

`pack --spec spec.json --source strategy.py --config config.json --out submission.json`。
spec 包含 `subject,submission_id,dataset_id,dataset_sha256,engine_sha256,seed,owner_key_id,
broker_key_id,recipient_key_id,issued_at,expires_at`，及三個公私鑰檔路徑
`owner_private_path,broker_public_path,recipient_public_path`。路徑相對 spec 檔。
submission_id 是隨機 32 位小寫 hex（例如 uuid4().hex）；期限為 Unix 秒，最多 24 小時。
上傳 submission.json 到 StratyUI「機密回測」，保留原提交檔供結果驗收。

下載密文後，依 `verify --help` / `decrypt --help` 提供原提交檔、
預期 subject、broker 簽署 key ID、公鑰及 QR 收件 key。decrypt 必須明確指定 `--out`；
stdout 不會印出明文，已有輸出檔亦不覆寫。資料量、執行時間與粗略狀態仍可能洩漏。

## 驗證語意

- execution succeeded：策略程序與可信帳務流程完成。
- verification passed：本 adapter 的帳務及歷史資料傳遞契約通過。
  每日損益 = 隔夜 + 日內 - 成本；FIFO 交易總損益須等於期末減初始權益。
- delivery available：密文與簽署收據已原子存妥、可下載，**不是**研究員已讀或已確認收件。
- research_qualification/oos/資料真實性：not_evaluated。無 OOS、過度擬合、完整市場成交、
  點時資料真實性、實盤可行性或獲利能力通過的主張。

保證金不足時拒絕該模擬；不暗中改口數或假裝完成追繳/強平模型。
固定口數使用簡單年化，不複利；沒有把 filter/帳務正確誤稱為 alpha。

## 金鑰輪替、故障及復原

Registry key 支援 `active`、`valid_from`、`expires_at`（Unix 秒）。先新增並可信分發
新公鑰版本，再撤銷舊版本；pending 工作停機後標 interrupted，重送必須使用新 ID。
Replay 唯一鍵是 stable subject + submission_id，改 signing key ID 不能重放。
收件公鑰固定在原提交，不能在工作途中偷偷换成 registry 最新公鑰。
舊 QR 收件私鑰與 broker 驗簽公鑰須保留，否則歷史結果無法解密/驗收。

SQLite 僅保存密文提交、密文結果與粗略狀態；備份仍需 ACL，不能刪掉 replay ledger 後
繼續使用舊 broker 身分接受工作。crash recovery 不自動重新執行，避免重放。
正常取消/逾時會移除指定容器；宿主 crash/daemon失聯後需由可信管理員檢查殘留
`straty-private-*` 容器並清理，確認完成後才重新接受工作。不要刪除其他容器。
回退時先停止新入口，保留私有 store/keys/ledger，不把機密工作轉到舊 runner。

## 驗收與正式切換

```sh
python -m pytest tests/test_graph_access.py tests/test_confidential*.py -q
STRATY_TEST_DOCKER_IMAGE=sha256:APPROVED_DIGEST python -m pytest tests/test_confidential_worker.py tests/test_confidential_e2e.py -q
```

無 Docker 環境變數時沙箱/E2E 測試會明確 skip；mock protocol 測試不能取代真實容器驗收。
UI 另跑現有 npm test 與 npm run build。

本次程式碼未切換 Kevin 正式服務、反代、帳號 ACL 或正式金鑰。正式切換需依全域
AGENTS.md 的 L3 規則確認：批准 release 與 image、研究員 subject/公鑰、資料快照、
專用服務帳號/ACL、OIDC header 映射與 HTTPS，再於維護窗口切換。舊部署保留供回退。
現有前端 lockfile 的 source-map-js advisory 應另外處理；此次未改動其依賴版本。
