import requests
import mysql.connector
from mysql.connector import Error
from sqlalchemy import create_engine
from sqlalchemy.exc import IntegrityError
import pymysql

from urllib import parse
import json
import pandas as pd

import schedule
import time


def create_engine_connection():
    engine = create_engine(f'mysql+pymysql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}/{DB_NAME}')
    return engine

# 데이터 가져오기
def get_highranked_data(api_key):
    tiers = ["CHALLENGER", "GRANDMASTER", "MASTER"]
    user_url = 'https://kr.api.riotgames.com/lol/league-exp/v4/entries/RANKED_SOLO_5x5/{}/I?page={}&api_key={}'
    user_tier = pd.DataFrame()

    for tier in tiers: 
        for page_num in range(1, 20):
            # URL 형식화
            url_now = user_url.format(tier, page_num, api_key)

            reqq = requests.get(url_now).text
            if reqq == '[]':
                pass
            else:
                df = json.loads(reqq)
                user_tier = pd.concat([user_tier, pd.DataFrame(df)], ignore_index=True)

    if not user_tier.empty:
        user_tier_df = user_tier.drop(['leagueId', 'queueType', 'rank', 'summonerId', 'inactive', 'freshBlood', 'hotStreak'], axis=1)
        return user_tier_df
    
    return pd.DataFrame()  # 빈 DataFrame 반환

# 주기적인 갱신 작업 (매일 한 번 실행)
def update_highranked_data():
    print("데이터 갱신 시작...")
    df = get_highranked_data(API_KEY)
    
    if not df.empty:

        engine = create_engine_connection()
        
        with engine.connect() as conn:
            conn.execute("TRUNCATE TABLE user_tier")  # 'user_tier' 테이블의 기존 데이터를 모두 삭제
        
        # 새 데이터 삽입 (갱신된 데이터)
        try:
            df.to_sql('user_tier', con=engine, if_exists='replace', index=False)  # 'replace'로 테이블을 덮어씁니다.
            print("Data successfully updated.")
        except IntegrityError as e:
            print(f"Error inserting data: {e}")
        
# 주기적인 작업 예약 (매일 한 번 갱신)
schedule.every(5).minutes.do(update_highranked_data)

# 계속 실행되도록 설정
if __name__ == "__main__":
    API_KEY = 'RGAPI-1e59aed9-d606-45e4-9389-17df7f63c8e2'
    DB_USER = 'root'
    DB_PASSWORD = '!!good8236'
    DB_HOST = 'localhost'
    DB_NAME = 'highrank_user'
    while True:
        schedule.run_pending()
        time.sleep(60)  # 1분마다 확인

        