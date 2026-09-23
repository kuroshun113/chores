"""J-OSLER の検索一覧で、テーブルの決まった位置にある「評価」ボタンを繰り返しクリックする。

JSF が生成する name / id（例: keikenGijutsuGinoForm:j_idt468:0:j_idt497）は
リロードのたびに変わることがあるので使わない。代わりに
「テーブルの N 行目・10 列目にある value="評価" のボタン」という位置で探す。

使い方:
    python click_review.py              # 1 行目の評価ボタンを 1 回クリック
    python click_review.py --repeat 5   # 5 回繰り返す
    python click_review.py --row 2      # 2 行目のボタンを対象にする
"""

import argparse

from playwright.sync_api import Page, TimeoutError as PlaywrightTimeoutError, sync_playwright

LIST_URL = "https://web.j-osler-jcs.jp/josler/sm1303/keikenGijutsuGinoKensakuIchiran.xhtml"

# ログイン状態（Cookie）を保存するフォルダ。2 回目以降はログインを省略できる。
PROFILE_DIR = "browser_profile"

# 評価ボタンがある列（1 始まり）。元の XPath の td[10]。
BUTTON_COLUMN = 10


def review_button(page: Page, row: int):
    """row 行目（1 始まり）の「評価」ボタンを返す。"""
    # 元の XPath から、変わる可能性のある name / id を除いて位置だけで指定したもの。
    xpath = (
        f"xpath=/html/body/div[1]/div/div[5]/form/div[2]/table/tbody"
        f"/tr[{row}]/td[{BUTTON_COLUMN}]/input[@value='評価']"
    )
    button = page.locator(xpath)
    if button.count() > 0:
        return button.first

    # ページのレイアウトが少し変わって上の XPath が外れたときの予備。
    # form 内のテーブルの row 行目・10 列目から探す。
    return (
        page.locator("form table tbody > tr")
        .nth(row - 1)
        .locator(f"td:nth-child({BUTTON_COLUMN}) input[value='評価']")
        .first
    )


def ensure_logged_in(page: Page) -> None:
    page.goto(LIST_URL)
    if page.locator("input[value='評価']").count() > 0:
        return
    input(
        "ブラウザでログインし、評価ボタンが並ぶ一覧（検索結果）を表示してから Enter を押してください..."
    )


def after_click(page: Page) -> None:
    """評価ボタンを押した後の操作をここに書く。

    例:
        page.mouse.wheel(0, 2000)              # 下にスクロール
        page.click("input[value='保存']")       # 別のボタンをクリック
        page.wait_for_load_state()
    """
    page.wait_for_load_state()


def return_to_list(page: Page) -> None:
    """一覧画面に戻る。画面に「戻る」ボタンがあるなら、それをクリックするほうが確実。"""
    page.go_back()
    page.wait_for_load_state()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--row", type=int, default=1, help="クリックする行（1 始まり）")
    parser.add_argument("--repeat", type=int, default=1, help="繰り返す回数")
    parser.add_argument("--wait", type=float, default=1.0, help="各回の間の待ち時間（秒）")
    args = parser.parse_args()

    with sync_playwright() as p:
        context = p.chromium.launch_persistent_context(PROFILE_DIR, headless=False)
        page = context.pages[0] if context.pages else context.new_page()

        ensure_logged_in(page)

        for i in range(1, args.repeat + 1):
            button = review_button(page, args.row)
            try:
                button.wait_for(state="visible", timeout=10_000)
            except PlaywrightTimeoutError:
                print(f"{args.row} 行目に評価ボタンが見つからないので終了します。")
                break

            print(f"[{i}/{args.repeat}] {args.row} 行目の評価ボタンをクリック")
            button.click()
            after_click(page)

            if i < args.repeat:
                return_to_list(page)
                page.wait_for_timeout(args.wait * 1000)

        input("完了しました。Enter でブラウザを閉じます...")
        context.close()


if __name__ == "__main__":
    main()
