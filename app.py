import os
import requests # ◀️ 追加
from datetime import datetime, timedelta # ◀️ 追加
from flask import Flask, request, Response

app = Flask(__name__)

# --- ここから追加 ---

# GitHub APIにアクセスするための共通ヘッダー
# トークンがあれば、より多くのリクエストが送れます（後述）

# GitHub APIにアクセスするための共通ヘッダー
HEADERS = {
    "Accept": "application/vnd.github.v3+json",
}
# トークンが存在する場合のみ、認証ヘッダーを追加


def get_user_events(username):
    """指定されたユーザーの公開イベント（活動履歴）を取得する関数"""
    url = f"https://api.github.com/users/{username}/events"
    try:
        # GitHub APIにリクエストを送信
        response = requests.get(url, headers=HEADERS)
        # もしリクエストが成功したら（ステータスコード 200）
        if response.status_code == 200:
            # 結果をJSON形式で返す
            return response.json()
        else:
            print(f"Error fetching GitHub events: {response.status_code}")
            return None
    except requests.exceptions.RequestException as e:
        print(f"Request error: {e}")
        return None

# --- ここまで追加 ---

# get_user_events 関数の下あたりに追加

def check_morning_coder(events):
    """「朝活コーダー」アチーブメントを判定する関数"""
    morning_commits = 0
    # 判定期間を「360日前から現在まで」に設定
    period_start = datetime.now() - timedelta(days=360)
    
    for event in events:
        # イベントの種類が 'PushEvent' (コミット) のものを探す
        if event['type'] == 'PushEvent':
            # イベントが発生した時刻を取得
            event_time_utc = datetime.strptime(event['created_at'], "%Y-%m-%dT%H:%M:%SZ")
            
            # イベントが判定期間内かチェック
            if event_time_utc > period_start:
                # GitHubの時間はUTC(協定世界時)なので、9時間足してJST(日本標準時)に変換
                event_time_jst = event_time_utc + timedelta(hours=9)
                
                # 日本時間の「時」が5, 6, 7, 8 のいずれかかをチェック
                if 5 <= event_time_jst.hour < 9:
                    # コミット数を加算
                    morning_commits += len(event['payload']['commits'])
    
    # コミット数が10回以上なら、アチーブメント情報を返す
    if morning_commits >= 10:
        return {
            "name": "☀️ Morning Coder",
            "description": f"朝活の証！朝の時間に {morning_commits} 回コミットしました。"
        }
    return None

def check_night_coder(events):
    """「夜活コーダー」アチーブメントを判定する関数"""
    night_commits = 0
    # 判定期間を「360日前から現在まで」に設定
    period_start = datetime.now() - timedelta(days=360)
    
    for event in events:
        # イベントの種類が 'PushEvent' (コミット) のものを探す
        if event['type'] == 'PushEvent':
            # イベントが発生した時刻を取得
            event_time_utc = datetime.strptime(event['created_at'], "%Y-%m-%dT%H:%M:%SZ")
            
            # イベントが判定期間内かチェック
            if event_time_utc > period_start:
                # GitHubの時間はUTC(協定世界時)なので、9時間足してJST(日本標準時)に変換
                event_time_jst = event_time_utc + timedelta(hours=9)
            
                if 18 <= event_time_jst.hour < 23 | 0<= event_time_jst.hour < 3:
                    # コミット数を加算
                    night_commits += len(event['payload']['commits'])
    
    # コミット数が10回以上なら、アチーブメント情報を返す
    if night_commits >= 1:
        return {
            "name": "🌕 Night Coder",
            "description": f"夜活の証！夜の時間に {night_commits} 回コミットしました。"
        }
    return None

def create_achievement_svg(unlocked_achievements):
    """アチーブメントのリストからSVG画像を生成する関数"""
    card_height = 70 + len(unlocked_achievements) * 35
    
    # アチーブメントリストのSVG部分を生成
    achievements_svg = ""
    for i, ach in enumerate(unlocked_achievements):
        y_pos = 60 + i * 35
        achievements_svg += f"""
            <text x="25" y="{y_pos}" class="title">{ach['name']}</text>
            <text x="25" y="{y_pos + 15}" class="desc">{ach['description']}</text>
        """
        
    # アチーブメントが一つもない場合のメッセージ
    if not unlocked_achievements:
        achievements_svg = '<text x="25" y="60" class="title">No achievements yet. Keep coding!</text>'

    # SVG全体のテンプレート
    svg_template = f"""
    <svg width="480" height="{card_height}" xmlns="http://www.w3.org/2000/svg">
      <style>
        .card {{ fill: #f9f9f9; stroke: #ddd; stroke-width: 1; border-radius: 8px; }}
        .header {{ font: bold 20px 'Segoe UI', Ubuntu, Sans-Serif; fill: #333; }}
        .title {{ font: bold 14px 'Segoe UI', Ubuntu, Sans-Serif; fill: #586069; }}
        .desc {{ font: 12px 'Segoe UI', Ubuntu, Sans-Serif; fill: #586069; }}
      </style>
      <rect class="card" x="0.5" y="0.5" width="479" height="99%" rx="8"/>
      <text x="25" y="35" class="header">My Original Achievements</text>
      {achievements_svg}
    </svg>
    """
    return svg_template



@app.route('/')
def index():
    return "こんにちは！アチーブメント画像生成サーバーです。"

@app.route('/api')
def generate_image():
    username = request.args.get('username')
    if not username:
        return Response('Error: No username specified.')

    events = get_user_events(username)
    if events is None:
        return Response(f'Error: Could not fetch data for {username}.')

    # --- ここからがデバッグ用のコード ---
    
    debug_output = f"<h1>{username}さんのPushイベントを調査中...</h1>"
    debug_output += "<h3>過去30日間のPushイベント（日本時間）:</h3><ul>"
    
    found_pushes = 0
    morning_commits_count = 0
    period_start = datetime.now() - timedelta(days=360)

    for event in events:
        if event['type'] == 'PushEvent':
            event_time_utc = datetime.strptime(event['created_at'], "%Y-%m-%dT%H:%M:%SZ")
            if event_time_utc > period_start:
                found_pushes += 1
                event_time_jst = event_time_utc + timedelta(hours=9)
                commit_count = len(event['payload']['commits'])
                
                # 朝の時間帯かをチェック
                is_morning = "☀️" if 0 <= event_time_jst.hour < 23 else " "
                if is_morning == "☀️":
                    morning_commits_count += commit_count

                debug_output += f"<li>{is_morning} {event_time_jst.strftime('%Y-%m-%d %H:%M:%S')} - コミット数: {commit_count}</li>"

    if found_pushes == 0:
        debug_output += "<li>見つかりませんでした。</li>"
    
    debug_output += "</ul>"
    debug_output += f"<hr><h3>調査結果:</h3>"
    debug_output += f"<p>判定期間内の朝コミット合計: <strong>{morning_commits_count}</strong> 回</p>"
    debug_output += f"<p>アチーブメント解除に必要な回数: <strong>10</strong> 回</p>"

    return Response(debug_output)

'''
 def generate_image():
    username = request.args.get('username')
    if not username:
        return Response('<svg><text>Error: No username specified.</text></svg>', mimetype='image/svg+xml')

    events = get_user_events(username)
    if events is None:
        return Response(f'<svg><text>Error: Could not fetch data for {username}.</text></svg>', mimetype='image/svg+xml')

    # --- アチーブメント判定をここで行う ---
    unlocked_achievements = []

    morning_coder = check_morning_coder(events)
    if morning_coder:
        unlocked_achievements.append(morning_coder)
        
    # 他のアチーブメントを追加する場合は、ここに判定関数呼び出しを追加していく

    # 判定結果を元にSVGを生成
    svg_content = create_achievement_svg(unlocked_achievements)

    # レスポンスヘッダーにキャッシュ制御を追加（1時間キャッシュさせる）
    response = Response(svg_content, mimetype='image/svg+xml')
    response.headers['Cache-Control'] = 'public, max-age=3600'
    return response
'''




if __name__ == '__main__':
    app.run(debug=True)