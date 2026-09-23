# J-OSLER 評価ボタン自動クリック

検索一覧のテーブルの決まった位置（デフォルトは 1 行目・10 列目）にある「評価」ボタンをクリックします。
ボタンの name / id（`j_idt468` など）はリロードのたびに変わるため使わず、位置で探します。

## セットアップ

```
pip install -r requirements.txt
playwright install chromium
```

## 実行

```
cd j_osler
python click_review.py                # 1 行目を 1 回
python click_review.py --repeat 5     # 5 回繰り返す
python click_review.py --row 2        # 2 行目を対象にする
```

1. ブラウザが開くので、ログインして評価ボタンが並ぶ一覧を表示し、ターミナルで Enter を押します。
2. ログイン状態は `browser_profile/` に保存され、次回以降はログインを省略できます（このフォルダは他人に渡さないこと）。

評価ボタンを押した後の操作（スクロールや別ボタンのクリック）は `after_click()` に、
一覧への戻り方は `return_to_list()` に書きます。
