# -*- coding=utf-8
'''
Created on 2016年9月23日

@author: zhaol
'''

class MFTDefine(object):
    """好友自建桌房间相关配置宏定义"""
    # 每轮多少局
    ROUND_COUNT = 'roundCount'
    # 当前局数
    CUR_ROUND_COUNT = 'curRoundCount'
    # 游戏一共多少圈
    QUAN_COUNT = 'quanCount'
    # 当前第几圈
    CUR_QUAN_COUNT = 'curQuanCount'
    # 几个底之芜湖麻将
    BASE_COUNT = 'BaseCount'
    # 当前第几个底之芜湖麻将
    CUR_BASE_COUNT = 'curBaseCount'
    # 玩家数量
    PLAYER_TYPE = 'playerType'
    # 房卡数量
    CARD_COUNT = 'cardCount'
    # 房卡计数类别
    # 按局计算房卡
    CARD_COUNT_ROUND = 'round'
    # 按圈计算房卡
    CARD_COUNT_CIRCLE = 'circle'
    # 按底计算房卡之芜湖麻将
    CARD_COUNT_BASE = 'base'
    # 玩家初始底分之芜湖麻将，根据牌码
    INIT_SCORE = 'init_score'
    # 剩余房卡数量，每两局减少一张房卡
    LEFT_CARD_COUNT = 'leftCardCount'
    # 是否自建桌
    IS_CREATE = 'iscreate'
    # 自建桌参数
    ITEMPARAMS = 'itemParams'
    # 自建桌号
    FTID = 'ftId'
    # 自建房主
    FTOWNER = 'ftOwner'
    # 自建房描述
    CREATE_TABLE_DESCS = 'create_table_desc_list'
    # 自建房描述
    CREATE_TABLE_OPTION_NAMES= 'create_table_option_name_list'
    # 自建房纯玩法描述(去除cardCount和playerType)
    CREATE_TABLE_PLAY_DESCS = 'create_table_play_desc_list'
    # 投票配置
    LEAVE_VOTE_NUM = 'leave_vote_num'
    # 投票配置-拒绝拒绝解散投票数
    REFUSE_LEAVE_VOTE_NUM = 'refuse_leave_vote_num'
    # 准备超时，超时自动释放房间
    READY_TIMEOUT = 'ready_max_timeout'
    # 无操作散桌超时
    CLEAR_TABLE_NO_OPTION_TIMEOUT = 'clear_table_no_option_timeout'
    # 是否允许吃
    ALLOW_CHI = 'allowChi'
    ALLOW_CHI_YES = 1
    ALLOW_CHI_NO = 0
    # 投票解散的特殊配置，有人拒绝就继续牌桌
    REFUSE_LEAVE_VOTE_NUM = 'refuse_leave_vote_num'
    # 必飘建房配置
    MUST_PIAO = 'mustPiao'
    # 必须自摸胡
    MUST_ZIMO = 'mustZimo'
    # 选项，不要风牌
    NO_FENG_TILES = 'no_feng_arrow_tiles'
    # 庄翻倍
    BANKER_DOUBLE = 'bankerDouble'
    # 门清翻倍
    CLEAR_DOUBLE = 'clearDouble'
    # 二五八掌
    ZHANG_258 = 'zhang258'
    # 是否乱锚
    LUAN_MAO = 'luanMao'
    # 最终结算分数是否要每局分
    BUDGET_INCLUDE_ROUND_SCORE = 'budget_include_round_score'
    # 是否后扣房卡,每第1,3,5...结束时扣除一张房卡(江西安徽采用这种模式)
    LATE_CONSUME_FANGKA = 'late_consume_fangka'
    # 经过了多少局，用来辅助后扣房卡,每第1,3,5...局结束时扣除一张房卡(江西安徽采用这种模式)
    PASSED_ROUND_COUNT = 'passed_round_count'
    # 后扣房卡方式里，已经扣了多少张房卡
    CONSUMED_FANGKA_COUNT = 'consumed_fangka_count'
    # 房卡ID
    CREATE_ITEM = 'create_item'
    # 是否可听
    CAN_TING = 'canTing'
    # 是否可漂
    CAN_PIAO = 'canPiao'
    # 是否可加倍
    CAN_DOUBLE = 'canDouble'
    # 附加大拿, 创建房间的参数，和县
    FU_JIA_DA_NA = 'fuJiaDaNa'
    # 刀子数额, 创建房间的参数，和县
    DAO_ZI = 'daozi'
    # 补花当作杠
    BU_FLOWER_AS_GANG = "bu_flower_as_gang"
    # 在出牌时计算胡牌
    CALC_WIN_TILES_AT_DROP = 'calc_win_tiles_at_drop'
    # 是否计算距离
    NEED_GEO = 'need_geo'
    def __init__(self):
        super(MFTDefine, self).__init__()
