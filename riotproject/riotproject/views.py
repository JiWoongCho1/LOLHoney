from django.shortcuts import render
from .models import Win_rate


def main_page(request):
    # 데이터를 처리하고 템플릿을 렌더링하는 코드
    cart_cnt, top_data = Win_rate().topList()
    cart_cnt, jg_data = Win_rate().jgList()
    cart_cnt, mid_data = Win_rate().midList()
    cart_cnt, bot_data = Win_rate().botList()
    
    return render(request, 'page_main.html',
                  {#"cart_cnt" : cart_cnt,  총 데이터 개수 
         "top_data" : top_data,
         "jg_data" : jg_data,
         "mid_data" : mid_data,
         "bot_data" : bot_data}
         )

# def cart_list(request):
#     # model(DB)처리
#     # Cart 생성하기
#     cart = Cart()
#     # 장바구니 전체 정보 조회하기
#     # - cart_cnt : 정수값
#     # - cart_list : [{'컬럼명' : 값 , '컬럼명' : 값 ...},{},{}]
#     cart_cnt, cart_list = cart.getcartList()
#     # 반환
#     return render(
#         request,
#         "riotproject/page_main.html",
#         {"챔피언" : cart_cnt,
#          "승률" : cart_list}
#     )