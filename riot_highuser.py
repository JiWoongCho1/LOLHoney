import requests

# import mysql.connector
# from mysql.connector import Error
from sqlalchemy import create_engine
import pymysql
import time
from urllib import parse
import json
import pandas as pd
import nest_asyncio
import asyncio
import aiohttp
from collections import defaultdict

nest_asyncio.apply()


# MySQL 테이블 생성 (필요할 경우)
def create_database_if_not_exists():
    try:
        connection = pymysql.connect(  ## mysql 연결  단순 작업이므로 connect 사용
            host=DB_HOST,
            user=DB_USER,
            password=DB_PASSWORD
        )
        cursor = connection.cursor() ## 데이터 통신 위한 객체 생성 

        cursor.execute(f"CREATE DATABASE IF NOT EXISTS {DB_NAME}")
        print(f"Database '{DB_NAME}' created or already exists.")

        # 연결 종료
        cursor.close()
        connection.close()

    except pymysql.MySQLError as e:
        print(f"Error creating database: {e}")

def get_highrankeduser_info_data(api_key, request_head):
    tiers = ["CHALLENGER", "GRANDMASTER", "MASTER"]
    # tiers = ["CHALLENGER"]
    # user_url = 'https://kr.api.riotgames.com/lol/league-exp/v4/entries/RANKED_SOLO_5x5/{}/I?page={}&api_key={}'
    # user_url = f'https://kr.api.riotgames.com/lol/league-exp/v4/entries/RANKED_SOLO_5x5/{tier}/I?page={page}'
    user_tier = pd.DataFrame()
    print('상위 티어 데이터 불러오는 중')
    
    for tier in tiers: 
        if tier == 'CHALLENGER':
            page_range = 2
        elif tier == 'GRANDMASTER':
            page_range = 4
        else:
            page_range = 20
        
        for page in range(1, page_range):
            user_url = f'https://kr.api.riotgames.com/lol/league-exp/v4/entries/RANKED_SOLO_5x5/{tier}/I?page={page}&api_key={api_key}'
            url_now = user_url.format(tier,page, api_key)
            reqq =  requests.get(url_now, request_head).text
            if reqq == '[]':
                pass
            else:
                df = json.loads(reqq)
                user_tier = pd.concat([user_tier, pd.DataFrame(df)], ignore_index=True)
            
    user_tier_df = user_tier.drop(['leagueId', 'queueType', 'rank', 'inactive', 'freshBlood', 'hotStreak'], axis = 1)
    print('PUUID 불러오는 중')
    puuids = []
    for summonerId in user_tier_df['summonerId']:
        user_puuids_url = f"https://kr.api.riotgames.com/lol/summoner/v4/summoners/{summonerId}?api_key={api_key}"
        response = requests.get(user_puuids_url, headers=request_head)
        
        if response.status_code == 200:  
            puuid = response.json().get('puuid')
            if puuid:  
                puuids.append(puuid)
            else:
                print(f"PUUID가 없는 응답: {response.json()}")
                puuids.append(None)  

        elif response.status_code == 429:  # Rate Limit 초과
              
            retry_after = int(response.headers.get("Retry-After", 10))  # Retry-After 헤더 값 확인 (없으면 10초)
            print(f"Rate Limit 초과. {retry_after}초 후 재시도...")
            time.sleep(retry_after)  # 대기 후 재시도
        

    
    while len(puuids) < len(user_tier_df):
        puuids.append(None)

    print(len(user_tier_df))
    return puuids


def get_match_data(puuids, api_key, request_head):
    start= 0 
    # count = 1
    count = 20

    top_champion_stats = defaultdict(lambda: {'wins': 0, 'games': 0, 'items': defaultdict(int)})
    jg_champion_stats = defaultdict(lambda: {'wins': 0, 'games': 0, 'items': defaultdict(int)})
    mid_champion_stats = defaultdict(lambda: {'wins': 0, 'games': 0, 'items': defaultdict(int)})
    ad_champion_stats = defaultdict(lambda: {'wins': 0, 'games': 0, 'items': defaultdict(int)})
    sup_champion_stats = defaultdict(lambda: {'wins': 0, 'games': 0, 'items': defaultdict(int)})

    combination_stats = defaultdict(lambda: {'games': 0, 'wins': 0})

    for puuid in puuids:
        if puuid == None:
            continue
        match_url = f"https://asia.api.riotgames.com/lol/match/v5/matches/by-puuid/{puuid}/ids?start={start}&count={count}"
        match_ids = requests.get(match_url, headers=request_head).json()

        match_info_list = []
        for match_id in match_ids:
            match_url = f"https://asia.api.riotgames.com/lol/match/v5/matches/{match_id}?api_key={api_key}"
            response = requests.get(match_url, headers=request_head)
            if response.status_code != 200:
                # print(f"Error: Received status code {response.status_code} for match ID {match_id}")
                # print(f"Response: {response.text}")  ## rate limit 주로 발생
                retry_after = int(response.headers.get("Retry-After", 10))  # Retry-After 헤더 값 확인 (없으면 10초)
                print(f"Rate Limit 초과. {retry_after}초 후 재시도...")
                time.sleep(retry_after)  # 대기 후 재시도
                
            else:
                if response.json()['info']['gameMode'] != 'CLASSIC': # Classic : rank
                    continue
                else:
                    match_info_list.append(response.json())


        for match in match_info_list:
            participants = match['info']['participants']
            lanes = {}
            lane_combinations = [
                ('TOP', 'JUNGLE'),
                ('MIDDLE', 'JUNGLE'),
                ('BOTTOM', 'UTILITY')
            ]    
            match_stat = pd.DataFrame(columns = ['champion', 'lane', 'win'])

            for participant in participants:
                champion = participant['championId']
                lane = participant['teamPosition']
                win = participant['win']
                
                items = [participant['item1'], participant['item2'], participant['item3'], participant['item4'], participant['item5'], participant['item6']]
                items = [item for item in items if item != 0]

                lanes[lane] = champion

                match_stat = match_stat.append({'champion': champion, 'lane': lane, 'win': win}, ignore_index=True)

                if lane == 'TOP':
                    top_champion_stats[champion]['games'] += 1
                    for item in items:
                        top_champion_stats[champion]['items'][item] += 1
                    if win:
                        top_champion_stats[champion]['wins'] += 2

                elif lane == 'JUNGLE':
                    jg_champion_stats[champion]['games'] += 1
                    for item in items:
                        jg_champion_stats[champion]['items'][item] += 1
                    if win:
                        jg_champion_stats[champion]['wins'] += 1

                elif lane == 'MIDDLE':
                    mid_champion_stats[champion]['games'] += 1
                    for item in items:
                        mid_champion_stats[champion]['items'][item] += 1
                    if win:
                        mid_champion_stats[champion]['wins'] += 1

                elif lane == 'BOTTOM':
                    
                    ad_champion_stats[champion]['games'] += 1
                    for item in items:
                        ad_champion_stats[champion]['items'][item] += 1
                    if win:
                        ad_champion_stats[champion]['wins'] += 1

                elif lane == 'UTILITY':
                    sup_champion_stats[champion]['games'] += 1
                    for item in items:
                        sup_champion_stats[champion]['items'][item] += 1
                    if win:
                        sup_champion_stats[champion]['wins'] += 1
            # print(match_stat)
            for lane1, lane2 in lane_combinations:
                combo = tuple(sorted([lanes[lane1], lanes[lane2]]))  # 순서 상관없이 같은 조합으로 처리
                # print(combo)
                # print([match_stat[match_stat['champion'] == champion]['win'] for champion in combo])
                win = all([match_stat[match_stat['champion'] == champion]['win'].iloc[0] for champion in combo])  # 둘 다 이겼는지 확인
                combination_stats[combo]['games'] += 1
                if win:
                    combination_stats[combo]['wins'] += 1
                

    top_champion_data = []
    jg_champion_data = []
    mid_champion_data = []
    ad_champion_data = []
    sup_champion_data = []

    result = []

    for combo, stats in combination_stats.items():
        win_rate = (stats['wins'] / stats['games']) * 100 if stats['games'] > 0 else 0
        result.append({
            'Combination': combo,
            'Games_Played': stats['games'],
            'Wins': stats['wins'],
            'Win_Rate': round(win_rate, 2)
        })

    
    for champion, stats in top_champion_stats.items():
        win_rate = stats['wins'] / stats['games'] * 100  # 승률을 백분율로 계산
        items_ = json.dumps(stats['items'])  
        top_champion_data.append({
            'key': champion,
            'Games_Played': stats['games'],
            'Wins': stats['wins'],
            'Win_Rate': round(win_rate, 2),
            'Items': items_
        })

    for champion, stats in jg_champion_stats.items():
        win_rate = stats['wins'] / stats['games'] * 100  # 승률을 백분율로 계산
        items_ = json.dumps(stats['items'])  
        jg_champion_data.append({
            'key': champion,
            'Games_Played': stats['games'],
            'Wins': stats['wins'],
            'Win_Rate': round(win_rate, 2),
            'Items': items_
        })

    for champion, stats in mid_champion_stats.items():
        win_rate = stats['wins'] / stats['games'] * 100  # 승률을 백분율로 계산
        items_ = json.dumps(stats['items'])  
        mid_champion_data.append({
            'key': champion,
            'Games_Played': stats['games'],
            'Wins': stats['wins'],
            'Win_Rate': round(win_rate, 2),
            'Items': items_
        })

    for champion, stats in ad_champion_stats.items():
        win_rate = stats['wins'] / stats['games'] * 100  # 승률을 백분율로 계산
        items_ = json.dumps(stats['items'])  
        ad_champion_data.append({
            'key': champion,
            'Games_Played': stats['games'],
            'Wins': stats['wins'],
            'Win_Rate': round(win_rate, 2),
            'Items': items_
        })

    for champion, stats in sup_champion_stats.items():
        win_rate = stats['wins'] / stats['games'] * 100  # 승률을 백분율로 계산
        items_ = json.dumps(stats['items'])  
        sup_champion_data.append({
            'key': champion,
            'Games_Played': stats['games'],
            'Wins': stats['wins'],
            'Win_Rate': round(win_rate, 2),
            'Items': items_
        })

    top_df_champion_stats = pd.DataFrame(top_champion_data)
    jg_df_champion_stats = pd.DataFrame(jg_champion_data)
    mid_df_champion_stats = pd.DataFrame(mid_champion_data)
    ad_df_champion_stats = pd.DataFrame(ad_champion_data)
    sup_df_champion_stats = pd.DataFrame(sup_champion_data)

    combo_df = pd.DataFrame(result)

    response = requests.get("https://ddragon.leagueoflegends.com/cdn/15.2.1/data/en_US/champion.json")
    data = response.json()
    df = pd.DataFrame(data['data']).T
    df = df[['id', 'key', 'name']]

    df['key'] = df['key'].astype('int64')
    champion_map = df.set_index('key')['id'].to_dict() 

    top_df_champion_stats['champion'] = top_df_champion_stats['key'].map(champion_map).fillna(top_df_champion_stats['key'])
    jg_df_champion_stats['champion'] = jg_df_champion_stats['key'].map(champion_map).fillna(jg_df_champion_stats['key'])
    mid_df_champion_stats['champion'] = mid_df_champion_stats['key'].map(champion_map).fillna(mid_df_champion_stats['key'])
    ad_df_champion_stats['champion'] = ad_df_champion_stats['key'].map(champion_map).fillna(ad_df_champion_stats['key'])
    sup_df_champion_stats['champion'] = sup_df_champion_stats['key'].map(champion_map).fillna(sup_df_champion_stats['key'])

    decoded_combos = []

    for combo in result: 
        champions = combo['Combination']
        
        decoded_combo = [champion_map.get(champion, champion) for champion in champions]
        
        decoded_combos.append({
            'Champion_Combo': tuple(decoded_combo),  # 디코딩된 조합
            'Games_Played': combo['Games_Played'],
            'Wins': combo['Wins'],
            'Win_Rate': combo['Win_Rate']
        })

    # 디코딩된 combo로 새로운 DataFrame 생성
    decoded_combo_df = pd.DataFrame(decoded_combos)

    return top_df_champion_stats, jg_df_champion_stats, mid_df_champion_stats, ad_df_champion_stats, sup_df_champion_stats, decoded_combo_df



def get_engine():
    create_database_if_not_exists()  # 데이터베이스가 없으면 생성
    engine = create_engine(f'mysql+pymysql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}/{DB_NAME}')  ## 데이터베이스 연결  하이 레벨의 연결 제공
    return engine

    


# def get_match_data(api_key):
#     puuids = 
#     match_url = f"https://asia.api.riotgames.com/lol/match/v5/matches/by-puuid/{puuids[0]}/ids?start={start}&count={count}"
#     match_ids = requests.get(match_url, headers=REQUEST_HEADERS).json()  ## 총 20개의 match data


if __name__ == "__main__":
    API_KEY = 'RGAPI-79190ab9-eb9b-4abb-a486-cb694c20cc07'
    REQUEST_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36",
    "Accept-Language": "ko-KR,ko;q=0.9,en-US;q=0.8,en;q=0.7",
    "Accept-Charset": "application/x-www-form-urlencoded; charset=UTF-8",
    "Origin": "https://developer.riotgames.com",
    "X-Riot-Token": API_KEY
    }

    DB_USER = 'root'
    DB_PASSWORD = '!!good8236'
    DB_HOST = 'localhost'
    DB_NAME = 'highrank_user'

    # summoner_data = get_summoner_data(summoner_name, tagLine)
    engine = get_engine()

    puuids = get_highrankeduser_info_data(API_KEY, REQUEST_HEADERS)
    top_df, jg_df, mid_df, ad_df, sup_df, combo_df =  get_match_data(puuids, API_KEY, REQUEST_HEADERS)
    combo_df['Champion_Combo'] = combo_df['Champion_Combo'].apply(lambda x: ', '.join(x))
 
    if not top_df.empty:
        top_df.to_sql('top_champion_winrate', con=engine, if_exists='replace', index=False)
    if not jg_df.empty:
        jg_df.to_sql('jg_champion_winrate', con=engine, if_exists='replace', index=False)
    if not mid_df.empty:
        mid_df.to_sql('mid_champion_winrate', con=engine, if_exists='replace', index=False)
    if not ad_df.empty:
        ad_df.to_sql('botchampion_rate', con=engine, if_exists='replace', index=False)
    if not sup_df.empty:
        sup_df.to_sql('supportchampion_rate', con=engine, if_exists='replace', index=False)
    if not combo_df.empty:
        combo_df.to_sql('combo_rate', con=engine, if_exists='replace', index=False)

    # batch_size= 1000
    # if not df.empty:
    #     df.to_sql('user_tier', con=engine, if_exists='replace', index=False)
    



        