"""J-OSLER の経験・技術・技能の検索一覧で、評価〜確定までを n 回繰り返す。

1 回分の流れ:
    一覧の N 行目の「評価」 → 知識・技能・態度のラジオ（value=3）を選択
    → 「承認」 → 「評価を確定する」 → 「戻る」で一覧に戻る

JSF が生成する name / id（例: keikenGijutsuGinoForm:j_idt468:0:j_idt497）は
リロードのたびに変わることがあるので使わず、位置やボタンの表示名（value）で探す。

使い方:
    python click_review.py --repeat 5          # 1 行目を 5 回評価
    python click_review.py --repeat 5 --row 2  # 2 行目を対象にする
    python click_review.py --repeat 5 --level 2
"""

import argparse

from playwright.sync_api import Page, TimeoutError as PlaywrightTimeoutError, sync_playwright

LIST_URL = "https://web.j-osler-jcs.jp/josler/sm1303/keikenGijutsuGinoKensakuIchiran.xhtml"

# ログイン状態（Cookie）を保存するフォルダ。2 回目以降はログインを省略できる。
PROFILE_DIR = "browser_profile"

# 評価ボタンがある列（1 始まり）。元の XPath の td[10]。
BUTTON_COLUMN = 10

# 評価画面のラジオボタンの name（知識・技能・態度）
RADIO_NAMES = [
    "keikenGijutsuGinoHyokaKekkaTorokuForm.chishiki",
    "keikenGijutsuGinoHyokaKekkaTorokuForm.gino",
    "keikenGijutsuGinoHyokaKekkaTorokuForm.taido",
]

# 画面遷移を待つ最大時間（ミリ秒）
PAGE_TIMEOUT = 30_000


def review_button(page: Page, row: int):
    """一覧の row 行目（1 始まり）の「評価」ボタンを返す。"""
    # 元の XPath から、変わる可能性のある name / id を除いて位置だけで指定したもの。
    xpath = (
        f"xpath=/html/body/div[1]/div/div[5]/form/div[2]/table/tbody"
        f"/tr[{row}]/td[{BUTTON_COLUMN}]/input[@value='評価']"
    )
    button = page.locator(xpath)
    if button.count() > 0:
        return button.first

    # ページのレイアウトが少し変わって上の XPath が外れたときの予備。
    return (
        page.locator("form table tbody > tr")
        .nth(row - 1)
        .locator(f"td:nth-child({BUTTON_COLUMN}) input[value='評価']")
        .first
    )


def submit_button(page: Page, value: str):
    return page.locator(f"input[type='submit'][value='{value}']").first


def click_and_wait_for(page: Page, button, next_button) -> None:
    """button をクリックし、次の画面の next_button が表示されるまで待つ。"""
    button.scroll_into_view_if_needed()
    button.click()
    next_button.wait_for(state="visible", timeout=PAGE_TIMEOUT)


def ensure_logged_in(page: Page) -> None:
    page.goto(LIST_URL)
    if page.locator("input[value='評価']").count() > 0:
        return
    input(
        "ブラウザでログインし、評価ボタンが並ぶ一覧（検索結果）を表示してから Enter を押してください..."
    )


def evaluate_once(page: Page, row: int, level: str) -> None:
    # 一覧 → 評価画面
    click_and_wait_for(page, review_button(page, row), submit_button(page, "承認"))

    # 知識・技能・態度のラジオを選択（ページ下方にあるのでスクロールしてからクリック）
    for name in RADIO_NAMES:
        radio = page.locator(f"input[type='radio'][name='{name}'][value='{level}']")
        radio.scroll_into_view_if_needed()
        radio.click()
        if not radio.is_checked():
            raise RuntimeError(f"ラジオボタンを選択できませんでした: {name}")

    # 承認 → 確認画面（2〜3 秒かかる）
    click_and_wait_for(page, submit_button(page, "承認"), submit_button(page, "評価を確定する"))

    # 評価を確定する → 完了画面
    click_and_wait_for(page, submit_button(page, "評価を確定する"), submit_button(page, "戻る"))

    # 戻る → 一覧
    submit_button(page, "戻る").click()
    page.wait_for_url(LIST_URL + "*", timeout=PAGE_TIMEOUT)
    page.wait_for_load_state()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repeat", type=int, required=True, help="評価を繰り返す回数 n")
    parser.add_argument("--row", type=int, default=1, help="クリックする行（1 始まり）")
    parser.add_argument("--level", default="3", help="ラジオボタンの value（3 = 専門医レベル）")
    parser.add_argument("--wait", type=float, default=1.0, help="各回の間の待ち時間（秒）")
    args = parser.parse_args()

    with sync_playwright() as p:
        context = p.chromium.launch_persistent_context(PROFILE_DIR, headless=False)
        page = context.pages[0] if context.pages else context.new_page()

        ensure_logged_in(page)

        answer = input(
            f"{args.row} 行目の評価を {args.repeat} 回確定します（取り消しできません）。"
            "よろしいですか？ [y/N]: "
        )
        if answer.strip().lower() != "y":
            print("中止しました。")
            context.close()
            return

        done = 0
        for i in range(1, args.repeat + 1):
            try:
                review_button(page, args.row).wait_for(state="visible", timeout=10_000)
            except PlaywrightTimeoutError:
                print(f"{args.row} 行目に評価ボタンが見つからないので終了します。")
                break

            print(f"[{i}/{args.repeat}] 評価中...")
            try:
                evaluate_once(page, args.row, args.level)
            except (PlaywrightTimeoutError, RuntimeError) as e:
                print(f"[{i}/{args.repeat}] 途中で止まりました。ブラウザの画面を確認してください。\n{e}")
                break
            done += 1
            print(f"[{i}/{args.repeat}] 確定しました")
            page.wait_for_timeout(args.wait * 1000)

        input(f"{done} 件確定しました。Enter でブラウザを閉じます...")
        context.close()


if __name__ == "__main__":
    main()
