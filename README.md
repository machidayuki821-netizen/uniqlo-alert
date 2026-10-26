# ユニクロ値下げ通知（GitHub Actions + LINE）

3時間ごとに価格を確認し、前回より安くなっていたら LINE に通知します。

## セットアップ
1. LINE Developers (https://developers.line.biz/) でプロバイダー→「Messaging API」チャネルを作成
2. チャネル設定で「チャネルアクセストークン（長期）」を発行
3. 作成したBotを自分のLINEで友だち追加
4. 「チャネル基本設定」下部の「あなたのユーザーID」(Uから始まる文字列) を控える
5. GitHubにこのリポジトリを push → Settings > Secrets and variables > Actions に登録
   - `LINE_CHANNEL_ACCESS_TOKEN`
   - `LINE_USER_ID`
6. Actions タブ > Uniqlo price check > Run workflow（test_notify を ON）で動作確認

※ LINE Notify は2025年3月で終了したため Messaging API を使用しています。
