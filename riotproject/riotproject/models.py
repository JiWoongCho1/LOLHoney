from django.db import models
import pymysql

class Mysql_Model :
    ### 생성자
    def __init__(self):
        self.initDBInfo()
        self.DBConnection()
        self.DBCursor()
        
    def initDBInfo(self):
        self.host = "localhost"
        self.user = "root"
        self.password = "!!good8236"
        self.db = "highrank_user"
        self.charset = "utf8"
        # 조회 시 컬럼명을 동시에 보여줄지 여부 설정
        self.cursorclass = pymysql.cursors.DictCursor
        self.autocommit = True
        
# - DB 접속
    def DBConnection(self):
        try :
            self.conn = pymysql.connect(
                host = self.host, user = self.user, password = self.password, 
                db = self.db, charset = self.charset, cursorclass = self.cursorclass, 
                autocommit = self.autocommit
            )
            print("DB 접속 성공 --> ", self.conn)
        except :
            print("DB 접속 정보 확인이 필요합니다")
        
# - DB로부터 cursor 받아오기
    def DBCursor(self):
        self.cur = self.conn.cursor()

    def DBClose(self):
        try :
            self.cur.close()
            self.conn.close()
            print("DB 정보 반환 완료....")
        except :
            print("이미 DB 정보가 반환되었습니다")


class Win_rate:
    def __init__(self):
        self.db = Mysql_Model()
        
    def topList(self):
        sql = """
        Select champion, Win_rate
        From top_champion_winrate
        Where games_played >= 50
        Order By games_played DESC
        """
        ### DB에 요청하기 : cursor에 담기
        # rs_cnt : 실행 결과의 건수
        rs_cnt = self.db.cur.execute(sql)
        # 실행 결과 데이터
        rows = self.db.cur.fetchall()
        # DB 정보 반환
        self.db.DBClose()
        return rs_cnt, rows
    
    def jgList(self):
        sql = """
        Select champion, Win_rate
        From jg_champion_winrate
        Where games_played >= 50
        Order By games_played DESC
        """
        rs_cnt = self.db.cur.execute(sql)
        rows = self.db.cur.fetchall()
        self.db.DBClose()
        return rs_cnt, rows
    
    def midList(self):
        sql = """
        Select champion, Win_rate
        From mid_champion_winrate
        Where games_played >= 50
        Order By games_played DESC
        """
        ### DB에 요청하기 : cursor에 담기
        # rs_cnt : 실행 결과의 건수
        rs_cnt = self.db.cur.execute(sql)
        # 실행 결과 데이터
        rows = self.db.cur.fetchall()
        # DB 정보 반환
        self.db.DBClose()
        return rs_cnt, rows
    
    def botList(self):
        sql = """
        Select champion, Win_rate
        From botchampion_rate
        Where games_played >= 50
        Order By games_played DESC
        """
        ### DB에 요청하기 : cursor에 담기
        # rs_cnt : 실행 결과의 건수
        rs_cnt = self.db.cur.execute(sql)
        # 실행 결과 데이터
        rows = self.db.cur.fetchall()
        # DB 정보 반환
        self.db.DBClose()
        return rs_cnt, rows