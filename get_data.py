import pandas as pd
import requests
import time
import os
import io

# ---------------------------------------------------------
# 設定
# ---------------------------------------------------------
# 2014年〜2023年
years = range(2014, 2024)
leagues = ['c', 'p']
all_data = []

print("強制スクレイピング開始...")

for year in years:
    for league in leagues:
        try:
            # -------------------------------------------------
            # 1. 打撃データ (tmb_c / tmb_p)
            # -------------------------------------------------
            url_bat = f"https://npb.jp/bis/{year}/stats/tmb_{league}.html"
            res = requests.get(url_bat, timeout=15)
            # 文字コードを自動で強引に合わせる
            res.encoding = res.apparent_encoding

            # ページ内の「全ての」表を読み込む
            try:
                dfs = pd.read_html(io.StringIO(res.text))
            except:
                print(f"× 読み込み失敗: {year} {league} 打撃")
                continue

            # 「行数が5より多い」かつ「列数が一番多い」表をデータとみなす
            # （チーム数は6なので、必ず6行以上あるはず）
            valid_dfs = [d for d in dfs if len(d) > 5]
            
            if not valid_dfs:
                print(f"× 表が見つからない: {year} {league} 打撃")
                continue
                
            df_bat = max(valid_dfs, key=lambda x: x.shape[1])

            # 1列目を「チーム」と決めつける
            df_bat.rename(columns={df_bat.columns[0]: 'チーム'}, inplace=True)
            
            # -------------------------------------------------
            # 2. 投手データ (tmp_c / tmp_p)
            # -------------------------------------------------
            url_pit = f"https://npb.jp/bis/{year}/stats/tmp_{league}.html"
            res_p = requests.get(url_pit, timeout=15)
            res_p.encoding = res_p.apparent_encoding
            
            try:
                dfs_p = pd.read_html(io.StringIO(res_p.text))
                valid_dfs_p = [d for d in dfs_p if len(d) > 5]
                if valid_dfs_p:
                    df_pit = max(valid_dfs_p, key=lambda x: x.shape[1])
                    df_pit.rename(columns={df_pit.columns[0]: 'チーム'}, inplace=True)
                else:
                    df_pit = pd.DataFrame(columns=['チーム']) # 空
            except:
                df_pit = pd.DataFrame(columns=['チーム']) # 空

            # -------------------------------------------------
            # 3. 整形と結合
            # -------------------------------------------------
            # チーム名に入っている余計な空白を削除
            df_bat['チーム'] = df_bat['チーム'].astype(str).str.replace(r'[\s　]+', '', regex=True)
            if not df_pit.empty:
                df_pit['チーム'] = df_pit['チーム'].astype(str).str.replace(r'[\s　]+', '', regex=True)
            
            # 強制結合 (outer)
            merged = pd.merge(df_bat, df_pit, on='チーム', how='outer', suffixes=('', '_投'))
            
            # 年度とリーグを追加
            merged.insert(0, '年度', year)
            merged.insert(1, 'リーグ', 'セ' if league == 'c' else 'パ')
            
            all_data.append(merged)
            print(f"○ 取得成功: {year}年 {league}リーグ ({len(merged)}件)")
            
            time.sleep(1)

        except Exception as e:
            print(f"エラー ({year} {league}): {e}")

# ---------------------------------------------------------
# 保存（文字化け対策：utf-8-sig）
# ---------------------------------------------------------
if len(all_data) > 0:
    final_df = pd.concat(all_data, ignore_index=True)
    
    # 勝利数カラムを空で作っておく
    final_df['勝利'] = ""
    
    # 列の整理（年度、リーグ、チーム、勝利...の順にする）
    cols = list(final_df.columns)
    priority_cols = ['年度', 'リーグ', 'チーム', '勝利']
    other_cols = [c for c in cols if c not in priority_cols]
    final_df = final_df[priority_cols + other_cols]

    os.makedirs('data', exist_ok=True)
    save_path = 'data/npb_data_final.csv'
    
    # ★ここが重要：Excel用の文字コードで保存
    final_df.to_csv(save_path, index=False, encoding='utf-8-sig')
    
    print(f"\n完了！データを保存しました: {save_path}")
    print("Excelで開いて文字化けしていないか確認し、'勝利'列を入力してください。")
    print(final_df.head())
else:
    print("\nデータが1件も取得できませんでした。")