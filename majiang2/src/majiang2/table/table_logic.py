# -*- coding=utf-8
'''
Created on 2016年9月23日
麻将的逻辑类，只关心麻将的核心玩法

新麻将的核心为牌桌状态及其对应的处理器。
切记，避免直接在状态与状态之间做切换。

@author: zhaol
'''
import time
from majiang2.ai.play_mode import MPlayMode
from majiang2.player.player import MPlayer, MPlayerTileGang
from majiang2.msg_handler.msg_factory import MsgFactory
from majiang2.action_handler.action_handler_factory import ActionHandlerFactory
from majiang2.table_state.state import MTableState
from majiang2.table_state_processor.drop_card_processor import MDropCardProcessor
from majiang2.table_state_processor.add_card_processor import MAddCardProcessor
from majiang2.banker.banker_factory import BankerFactory
from majiang2.win_rule.win_rule_factory import MWinRuleFactory
from majiang2.win_rule.win_rule import MWinRule
from majiang2.table_tile.table_tile import MTableTile
from majiang2.table_tile.table_tile_factory import MTableTileFactory
from majiang2.table_state.state_factory import TableStateFactory
from majiang2.player.hand.hand import MHand
from majiang2.table.run_mode import MRunMode
from majiang2.ting_rule.ting_rule_factory import MTingRuleFactory
import copy
from majiang2.chi_rule.chi_rule_factory import MChiRuleFactory
from majiang2.peng_rule.peng_rule_factory import MPengRuleFactory
from majiang2.gang_rule.gang_rule_factory import MGangRuleFactory
from freetime.util import log as ftlog
from majiang2.table_state_processor.extend_info import MTableStateExtendInfo
from majiang2.win_loose_result.one_result_factory import MOneResultFactory
from majiang2.win_loose_result.one_result import MOneResult
from majiang2.win_loose_result.round_results import MRoundResults
from majiang2.win_loose_result.table_results import MTableResults
from majiang2.tile.tile import MTile
from majiang2.table_state_processor.qiang_gang_hu_processor import MQiangGangHuProcessor
import poker.util.timestamp as pktimestamp
from majiang2.table.friend_table_define import MFTDefine
from majiang2.table.table_config_define import MTDefine
from majiang2.table_statistic.statistic import MTableStatistic
from majiang2.table_state_processor.absence_processor import MAbsenceProcessor
from majiang2.table_state_processor.change3tiles_processor import MChange3tilesProcessor
from majiang2.table_state_processor.qiangjin_processor import MQiangjinProcessor
from majiang2.table_state_processor.zhisaizi_processor import ZhisaiziProcessor
from majiang2.table_state_processor.kaijin_processor import KaijinProcessor
from majiang2.table_state_processor.flower_processor import MFlowerProcessor
from majiang2.table_state_processor.piao_processor import MPiaoProcessor
from majiang2.table_state_processor.qiang_exmao_peng_processor import MQiangExmaoPengProcessor
from majiang2.table_state_processor.qiang_exmao_hu_processor import MQiangExmaoHuProcessor
from majiang2.entity.util import Util
from majiang2.mao_rule.mao_rule_factory import MMaoRuleFactory
#from majiang2.flower_rule.flower_base import MFlowerRuleBase
from majiang2.flower_rule.flower_rule_factory import MFlowerRuleFactory
from majiang2.entity.item import MajiangItem
from majiang2.banker.banker import MBanker
from majiang2.table_state_processor.double_processor import MDoubleProcessor
from majiang2.servers.util.rpc import user_remote
from majiang2.table_state_processor.ting_before_add_card_processor import MTingBeforeAddCardProcessor
from majiang2.table_state_processor.tian_ting_processor import MTianTingProcessor
from majiang2.table_state_processor.lou_hu_processor import MLouHuProcessor
from majiang2.ai.ting import MTing
from majiang2.gua_da_feng_rule.dafeng_base import MDaFengRuleBase
from majiang2.table_state_processor.da_feng_processor import MDafengProcessor
from majiang2.entity import util
from majiang2.table.geo_mixin import GEOMixin
import datetime
import time
class MajiangTableLogic(object):
    def __init__(self, playerCount, playMode, runMode):
        super(MajiangTableLogic, self).__init__()
        # 用户数量
        self.__playerCount = playerCount
        # 玩法
        self.__playMode = playMode
        # 运行方式
        self.__run_mode = runMode
        # 牌桌配置
        self.__table_config = {}
        # 根据玩法获取发牌器
        self.__table_tile_mgr = MTableTileFactory.getTableTileMgr(self.__playerCount, self.__playMode, runMode)
        # 本局玩家
        self.__players = [ None for _ in range(self.playerCount) ]

	#modify by yj 05.08
        # 本局玩家杠的得分信息[[2,0,-2],[4,-2,-2],[0,0,0]]
        self.__gang_scores = [[0 for _ in range(self.playerCount)] for _ in range(self.playerCount) ]
        # 玩家网络状态
        self.__players_ping = {}
        # 手牌张数
        self.__hand_card_count = 13
        # 庄家
        self.__banker_mgr = BankerFactory.getBankerAI(self.playMode)
        # 当前操作座位号
        self.__cur_seat = 0
        # 上牌状态
        self.__add_card_processor = MAddCardProcessor()
        # 上牌前的听牌状态
        self.__ting_before_add_card_processor = MTingBeforeAddCardProcessor()
        # 漏胡处理器
        self.__lou_hu_processor = MLouHuProcessor()
        # 刮大风处理器
        self.__da_feng_processor = MDafengProcessor()
        # 出牌状态
        self.__drop_card_processor = MDropCardProcessor(self.playerCount, playMode)
        self.__drop_card_processor.setTableTileMgr(self.tableTileMgr)
        # 抢杠和状态
        self.__qiang_gang_hu_processor = MQiangGangHuProcessor(self.playerCount)
        self.__qiang_gang_hu_processor.setTableTileMgr(self.tableTileMgr)
        # 抢锚碰状态
        self.__qiang_exmao_peng_processor = MQiangExmaoPengProcessor(self.playerCount)
        # 抢锚碰状态
        self.__qiang_exmao_hu_processor = MQiangExmaoHuProcessor(self.playerCount)
        # 定飘的处理器
        self.__piao_processor = MPiaoProcessor(self.playerCount, playMode)
        self.__piao_processor.setTableTileMgr(self.tableTileMgr)
        # 翻倍的处理器
        self.__double_processor = MDoubleProcessor(self.playerCount, playMode)
        # 定缺的处理器
        self.__absence_processor = MAbsenceProcessor(self.playerCount, playMode)
        # 换三张的处理器
        self.__change3tilesProcessor = MChange3tilesProcessor(self.playerCount,playMode)
	self.__change3tilesProcessor.setBankerMgr(self.bankerMgr)
	self.__qiangjinProcessor = MQiangjinProcessor(self.playerCount,playMode)
	# 掷塞子的处理器
        self.__zhisaizi_processor = ZhisaiziProcessor(self.playerCount, playMode)
        # 补花的处理器
        self.__flower_processor = MFlowerProcessor(self.playerCount, playMode)
        # 和牌状态
        self.__table_win_state = MTableState.TABLE_STATE_NONE
        # 消息处理者
        self.__msg_processor = MsgFactory.getMsgProcessor(runMode)
        self.__msg_processor.setTableTileMgr(self.tableTileMgr)
        # 游戏开始前的听牌状态
        self.__tian_ting_processor = MTianTingProcessor(self.playerCount)
        self.__tian_ting_processor.setMsgProcessor(self.msgProcessor)
        # 牌桌状态机
        self.__table_stater = TableStateFactory.getTableStates(self.playMode)
        self.__table_stater.setPlayMode(self.playMode)  
        # 吃牌AI
        self.__chi_rule_mgr = MChiRuleFactory.getChiRule(self.playMode)
        self.__chi_rule_mgr.setTableTileMgr(self.tableTileMgr)
        # 碰牌AI
        self.__peng_rule_mgr = MPengRuleFactory.getPengRule(self.playMode)
        self.__peng_rule_mgr.setTableTileMgr(self.tableTileMgr)
        # 杠牌AI
        self.__gang_rule_mgr = MGangRuleFactory.getGangRule(self.playMode)
        self.__gang_rule_mgr.setTableTileMgr(self.tableTileMgr)
        self.__gang_rule_mgr.setTableStates(self.tableStater)
        # 花AI
        self.__flower_rule_mgr = MFlowerRuleFactory.getFlowerRule(self.playMode)
	# 开金的处理器
        self.__kaijin_processor = KaijinProcessor(self.playerCount, playMode)
        self.__kaijin_processor.setTableTileMgr(self.tableTileMgr)
        # 和牌管理器
	ftlog.debug('MajiangTableLogic.playMode=',self.playMode)
        self.__win_rule_mgr = MWinRuleFactory.getWinRule(self.playMode)
        self.__win_rule_mgr.setTableTileMgr(self.tableTileMgr)
        self.__win_rule_mgr.setTableConfig(self.tableConfig)
        # 锚牌管理器
        self.__mao_rule_mgr = MMaoRuleFactory.getMaoRule(self.playMode)
        # 听牌管理器
        if self.checkTableState(MTableState.TABLE_STATE_TING):
            self.__ting_rule_mgr = MTingRuleFactory.getTingRule(self.playMode)
            self.__ting_rule_mgr.setWinRuleMgr(self.__win_rule_mgr)
            self.__ting_rule_mgr.setTableTileMgr(self.tableTileMgr)
	    if MPlayMode().isSubPlayMode(self.playMode, MPlayMode.QUESHOU):
                self.__ting_rule_mgr.setFlowerRule(self.__flower_rule_mgr)
        else:
            self.__ting_rule_mgr = None
        # 牌桌最新操作标记，摸牌actionID加1，出牌actionID加1

        self.__action_id = 0
        # 圈/风
        self.__quan_men_feng = 0
        # 算分结果
        self.__round_result = None
        # 牌桌结果
        self.__table_result = MTableResults()
        # 牌局记录上传记录url
        self.__record_url = []
        # 牌局记录每局底和局数
        self.__record_base_id = []
        # 记录上一局的结果
        self.__win_loose = 0
        # 记录上一局的胜利者
        self.__last_win_seatId = 0
        self.__last_wins = []  # 一炮多响时，上一局有多个胜利者
        # 大赢家userId,用于配置了大赢家支付房卡选项时,在自建桌最终结算时扣除大赢家的房卡
        self.__biggest_winner = 0
	# 记录上一局的输家们
        self.__last_looses = []
        # 杠牌记录,用来判定杠上花和杠上炮,每次成功杠牌后设置,每次出牌后或者抢杠胡后清空,设置值为座位号,默认值-1

        self.__latest_gang_state = -1
        # 牌桌观察者
        self.__table_observer = None
        # 牌桌类型
        self.__table_type = MTDefine.TABLE_TYPE_NORMAL
        # 投票之后底需要结算
        self.__voteFinal = 0
        # 发起解散的人
        self.__vote_host = -1
        # 游戏ID
        self.__gameId = 0
        self.__roomId = 0
        self.__tableId = 0
        self.__bigRoomId = 0
	self.__qiangjin = False
	self.__flower_round = 1
        #获取距离
        self.__geo_mixin = GEOMixin(self.__playerCount,self.__msg_processor)

    def setGameInfo(self, gameId, bigRoomId, roomId, tableId):
        self.__gameId = gameId
        self.__bigRoomId = bigRoomId
        self.__roomId = roomId
        self.__tableId = tableId

    @property
    def gameId(self):
        return self.__gameId

    @property
    def bigRoomId(self):
        return self.__bigRoomId

    @property
    def roomId(self):
        return self.__roomId

    @property
    def tableId(self):
        return self.__tableId

    @property
    def biggestWinner(self):
        return self.__biggest_winner

    def setBiggestWinner(self, winner):
        self.__biggest_winner = winner

    @property
    def maoRuleMgr(self):
        return self.__mao_rule_mgr

    def setMaoRuleMgr(self, maoRuleMgr):
        self.__mao_rule_mgr = maoRuleMgr

    @property
    def lastWinSeatId(self):
        return self.__last_win_seatId
    
    def setLastWinSeatId(self, lastWinSeatId):
        self.__last_win_seatId = lastWinSeatId

    @property
    def lastWins(self):
        return self.__last_wins

    def setLastWins(self, lastWins):
        self.__last_wins = lastWins[:]

    @property
    def lastLooses(self):
        return self.__last_looses

    def setLastLooses(self, lastLooses):
        self.__last_looses = lastLooses[:]

    @property
    def winLoose(self):
        return self.__win_loose
    
    def setWinLoose(self, winLoose):
        self.__win_loose = winLoose
    
    @property
    def bankerMgr(self):
        return self.__banker_mgr
    
    def setBankerMgr(self, bankerMgr):
        self.__banker_mgr = bankerMgr
        
    @property
    def tableStater(self):
        return self.__table_stater
    
    def setTableStater(self, tableStater):
        self.__table_stater = tableStater
        
    @property
    def chiRuleMgr(self):
        return self.__chi_rule_mgr
    
    def setChiRuleMgr(self, chiRuleMgr):
        self.__chi_rule_mgr = chiRuleMgr
    
    @property
    def pengRuleMgr(self):
        return self.__peng_rule_mgr
    
    def setPengRuleMgr(self, pengRuleMgr):
        self.__peng_rule_mgr = pengRuleMgr
    
    @property
    def gangRuleMgr(self):
        return self.__gang_rule_mgr
    
    def setGangRuleMgr(self, gangRuleMgr):
        self.__gang_rule_mgr = gangRuleMgr
    @property
    def flowerRuleMgr(self):
        return self.__flower_rule_mgr
    
    def setflowerRuleMgr(self, flowerRuleMgr):
        self.__flower_rule_mgr = flowerRuleMgr 
       
    @property
    def tableType(self):
        return self.__table_type
    
    def setTableType(self, tableType):
        self.__table_type = tableType
        
    def setLatestGangState(self, state):
        self.__latest_gang_state = state
        
    @property
    def latestGangState(self):
        return self.__latest_gang_state
    
    @property
    def tableResult(self):
        return self.__table_result
    
    def setTableResult(self, tableResult):
        self.__table_result = tableResult
    
    @property
    def recordUrl(self):
        return self.__record_url
    
    def setRecordUrl(self, recordUrl):
        self.__record_url = recordUrl

    @property
    def recordBaseId(self):
        return self.__record_base_id

    def setRecordBaseId(self, recordBaseId):
        self.__record_base_id = recordBaseId

    @property
    def tableWinState(self):
        return self.__table_win_state
    
    def setTableWinState(self, tableWinState):
        self.__table_win_state = tableWinState
    def getFangkaPayConfig(self):
        """获取房卡支付配置"""
        ftlog.info('getFangkaConfig info:', self.tableConfig)
        fangka_pay = self.tableConfig.get(MTDefine.FANGKA_PAY,0)
        ftlog.info('getFangkaConfig info:', fangka_pay)
        return fangka_pay    
    def nextRound(self):
        """下一把"""
        self.setCurSeat(0)
	self.setBiggestWinner(0)
        self.addCardProcessor.reset()
        self.tingBeforeAddCardProcessor.reset()
        self.tianTingProcessor.reset()
        self.dropCardProcessor.reset()
        self.qiangGangHuProcessor.reset()
        self.qiangExmaoPengProcessor.reset()
        self.qiangExmaoHuProcessor.reset()
        self.piaoProcessor.reset()
        self.zhisaiziProcessor.reset()
        self.flowerProcessor.reset()
        self.kaijinProcessor.reset()
        self.doubleProcessor.reset()
        self.setTableWinState(MTableState.TABLE_STATE_NONE)
        ftlog.info('MajiangTableLogic.nextRound tableWinState:', self.__table_win_state)
    	self.__qiangjin = False    
        self.setActionId(0)
        self.setQuanMenFeng(0)
        self.setVoteFinal(0)
        self.setVoteHost(-1)
        self.tableTileMgr.reset()
	self.__flower_round = 1       
        for player in self.player:
            if player:
                player.reset()
                
    @property
    def tableObserver(self):
        return self.__table_observer
    
    def setTableObserver(self, observer):
        self.__table_observer = observer
        
    @property
    def roundResult(self):
        return self.__round_result
    
    def setRoundResult(self, roundResult):
        self.__round_result = roundResult

    @property
    def runMode(self):
        return self.__run_mode
    
    def setRunMode(self, runMode):
        self.__run_mode = runMode
    
    def isCountByRound(self):
        """当前牌桌用局计量"""
        return (self.getTableConfig(MFTDefine.ROUND_COUNT, 0) > 0) and (self.getTableConfig(MFTDefine.ROUND_COUNT, 0) != 999999)
    
    def isCountByQuan(self):
        """当前牌桌用圈计量"""
        return self.getTableConfig(MFTDefine.QUAN_COUNT, 0) > 0

    def isOverByBase(self):
        """
        根据玩家底的次数和底分判断游戏是否结束，前提是玩家初始分不为0
        """
        ftlog.debug('MajiangTableLogic.isCountByBase left base count:', self.tableConfig[MFTDefine.CUR_BASE_COUNT])
        if self.tableConfig.get(MTDefine.OVER_BY_SCORE, 0):
            if self.isPlayerFinal():
                if self.isFinal():
                    return True
                elif self.isBaseFinal():
                    # 这个底打完了 先出这个底的结算 还有底要打 不能清table 返回false
                    self.sendCreateExtendBudgetsInfo(0)
                    # 本底打完 ＋1
                    self.tableConfig[MFTDefine.CUR_BASE_COUNT] += 1
                    self.tableConfig[MFTDefine.CUR_ROUND_COUNT] = 0
                    return False

        return False
    
    @property
    def voteFinal(self):
        return self.__voteFinal

    def setVoteFinal(self, final):
        self.__voteFinal = final
        
    @property
    def voteHost(self):
        return self.__vote_host
    
    def setVoteHost(self, voteHost):
        ftlog.debug('MajiangTableLogic.setVoteHost:', voteHost)
        self.__vote_host = voteHost

    def isPlayerFinal(self):
        """
         是否需要结算
        """
        curBaseCount = self.tableConfig[MFTDefine.CUR_BASE_COUNT]
        if curBaseCount <= 0:
            return False

        for player in self.player:
            if player and player.getCurScoreByBaseCount(curBaseCount) <= 0:
                ftlog.debug('MajiangTableLogic.isPlayerFinal true')
                return True

        if self.voteFinal:
            return True

        return False

    def isBaseFinal(self):
        """
        是否有底结算
        """
        return self.tableConfig[MFTDefine.BASE_COUNT] > 1

    def isFinal(self):
        """
        是否是大结算
        """
        return self.voteFinal or self.tableConfig[MFTDefine.CUR_BASE_COUNT] == self.tableConfig[MFTDefine.BASE_COUNT]

    def resetGame(self, winLoose):
        """重置游戏"""
        self.__win_loose = winLoose
        self.__last_win_seatId = self.curSeat
	#modify by yj 05.08
        self.__gang_scores = [[0 for _ in range(self.playerCount)] for _ in range(self.playerCount) ] 

        # 当前游戏信息备忘
        finishBanker = self.queryBanker()
        userIds = self.getBroadCastUIDs()
        # 确定下一局的庄家
        curRoundCount = self.tableConfig.get(MFTDefine.CUR_ROUND_COUNT, 0)
        lastSeatId = self.__last_win_seatId
        if len(self.lastWins) > 1 and len(self.lastLooses) > 0:  # 一炮多响时赋值为输家
            lastSeatId = self.lastLooses[0]

        newbanker = 0
        remains = 0 
        noresults = 0 
	
        if (self.playMode == 'luosihu-ctxuezhan') or self.playMode == 'luosihu-xuezhan':
            newbanker,remains,noresults = self.bankerMgr.getBankerForXueZhan(self.__playerCount
                ,(curRoundCount == 0)
                , self.__win_loose
                ,self.players
                ,self.roundResult.score)
        else:
            newbanker, remains, noresults = self.bankerMgr.getBanker(self.__playerCount
                , (curRoundCount == 0)
                , self.__win_loose
                , lastSeatId
                , {MBanker.GANG_COUNT: self.tableTileMgr.gangCount})
	#modify by youjun 04.25
        if self.checkTableState(MTableState.TABLE_STATE_XUEZHAN):
            for player in self.player:
                player.setHasHu(False)
                player.setXuezhanRank(100)
	#modify end
        # 牌桌记录生成
        recordName = self.getCreateTableRecordName()
        recordUrl = self.msgProcessor.saveRecord(recordName)
        self.__record_url.append(recordUrl)
        # 牌桌记录底和局数生成
        curBaseCount = self.tableConfig.get(MFTDefine.CUR_BASE_COUNT, 0)
        if curBaseCount > 0:
            curCount = self.tableConfig[MFTDefine.CUR_ROUND_COUNT]
            tableBaseNoStr = str(curBaseCount) + " " + str(curCount) # tableBaseNoStr:'1 2' 1底 2局
            self.recordBaseId.append(tableBaseNoStr)
        # 标记游戏结束状态
        self.__table_win_state = MTableState.TABLE_STATE_GAME_OVER
        # 牌局手牌管理器reset
        self.tableTileMgr.reset()
        # 游戏结束后，记录牌局事件
        if self.tableObserver:
            # 游戏事件记录
            self.tableObserver.onBeginGame(userIds, finishBanker)
            self.tableObserver.onGameEvent(MTableStatistic.TABLE_WIN
                    , self.player
                    , self.getTableConfig(MTDefine.TABLE_ROUND_ID, pktimestamp.getCurrentTimestamp()))
        # 清空__round_result 否则在一局结束下局未开始时断线重连会取到错误的积分数据
        self.__round_result = MRoundResults()
        self.piaoProcessor.reset()

        self.change3tilesProcessor.reset()
        self.absenceProcessor.reset()
	self.qiangjinProcessor.reset()	

    def reset(self):
        """重置"""
        self.nextRound()
        self.bankerMgr.reset()
        self.setPlayer([ None for _ in range(self.playerCount) ])
	self.geoMixin.reset()
        self.setRoundResult(None)
        self.tableResult.reset()
        self.piaoProcessor.resetPiaoCount()
        self.doubleProcessor.reset()
        self.setRecordUrl([])
        self.setRecordBaseId([])
        self.tableConfig[MFTDefine.CUR_ROUND_COUNT] = 0
        self.msgProcessor.reset()
        
    @property
    def tingRule(self):
        """听牌规则管理器"""
        return self.__ting_rule_mgr

    @property
    def geoMixin(self):
        return self.__geo_mixin
    
    @property
    def addCardProcessor(self):
        """摸牌管理器"""
        return self.__add_card_processor
    
    @property
    def tingBeforeAddCardProcessor(self):
        return self.__ting_before_add_card_processor
    
    def setTingBeforeAddCardProcessor(self, processor):
        self.__ting_before_add_card_processor = processor

    @property
    def tianTingProcessor(self):
        return self.__tian_ting_processor

    @property
    def louHuProcesssor(self):
        return self.__lou_hu_processor
    
    def setLouHuProcessor(self, louHuProcessor):
        self.__lou_hu_processor = louHuProcessor
        
    @property
    def daFengProcessor(self):
        return self.__da_feng_processor
    
    def setDaFengProcessor(self, processor):
        self.__da_feng_processor = processor
    
    @property
    def dropCardProcessor(self):
        """出牌管理器"""
        return self.__drop_card_processor
    
    @property
    def qiangGangHuProcessor(self):
        return self.__qiang_gang_hu_processor
    
    @property
    def qiangExmaoPengProcessor(self):
        return self.__qiang_exmao_peng_processor
    
    @property
    def qiangExmaoHuProcessor(self):
        return self.__qiang_exmao_hu_processor

    @property
    def change3tilesProcessor(self):
        return self.__change3tilesProcessor

    def setChange3tilesProcessor(self , change3tilesProcessor):
        self.__change3tilesProcessor = change3tilesProcessor

    @property
    def absenceProcessor(self):
        return self.__absence_processor

    def setAbsenceProcessor(self, absenceProcessor):
        self.__absence_processor = absenceProcessor

    @property
    def piaoProcessor(self):
        return self.__piao_processor
    
    def setPiaoProcessor(self, piaoProcessor):
        self.__piao_processor = piaoProcessor

    @property
    def qiangjinProcessor(self):
        return self.__qiangjinProcessor
    
    def setQiangjinProcessor(self,qiangjinProcessor):
        self.__qiangjinProcessor = qiangjinProcessor

    @property
    def zhisaiziProcessor(self):
        return self.__zhisaizi_processor

    def setZhisaiziProcessor(self, zhisaiziProcessor):
        self.__zhisaizi_processor = zhisaiziProcessor

    @property
    def kaijinProcessor(self):
        return self.__kaijin_processor

    def setKaijinProcessor(self, kaijinProcessor):
        self.__kaijin_processor = kaijinProcessor

    @property
    def flowerProcessor(self):
        return self.__flower_processor

    def setFlowerProcessor(self, flowerProcessor):
        self.__flower_processor = flowerProcessor
        
    @property
    def doubleProcessor(self):
        return self.__double_processor
    
    def setDoubleProcessor(self, doubleProcessor):
        self.__double_processor = doubleProcessor
            
    @property
    def playerCount(self):
        """获取本局玩家数量"""
        return self.__playerCount
    
    @property
    def msgProcessor(self):
        """获取消息处理对象"""
        return self.__msg_processor
    
    @property
    def actionID(self):
        """获取当前的操作标记"""
        return self.__action_id
    
    def incrActionId(self, reason):
        self.__action_id += 1
        ftlog.info('MajiangTableLogic.incrActionId now:', self.actionID
                   , ' reason:', reason)

    def setActionId(self, actionId):
        ftlog.info('tableLogic.setActionId now:', self.__action_id
                   , ' actionId:', actionId) 
        self.__action_id = actionId
    
    @property
    def playMode(self):
        """获取本局玩法"""
        return self.__playMode
    
    def setPlayMode(self, playMode):
        self.__playMode = playMode
    
    @property
    def player(self):
        """获取玩家"""
        return self.__players
    
    @property
    def players(self):
        return self.__players
    
    def setPlayer(self, player):
        self.__players = player

    def gangScores(self):
        return self.__gang_scores
    
    @property
    def quanMenFeng(self):
        """获取圈/风设置"""
        return self.__quan_men_feng
    
    def setQuanMenFeng(self, quanMenFeng):
        self.__quan_men_feng = quanMenFeng
    
    @property
    def handCardCount(self):
        """获取初始手牌张数
        """
        return self.__hand_card_count
    
    def setHandCardCount(self, count):
        """设置初始手牌张数
        """
        self.__hand_card_count = count
        
    @property
    def curSeat(self):
        """当前操作座位号
        """
        return self.__cur_seat
    
    def setCurSeat(self, seat):
        """设置当前操作座位号
        """
        self.__cur_seat = seat
    @property
    def tableTileMgr(self):
        return self.__table_tile_mgr
    
    def setTableTileMgr(self, tableTileMgr):
        self.__table_tile_mgr = tableTileMgr
    
    @property
    def winRuleMgr(self):
        return self.__win_rule_mgr
    
    def setWinRuleMgr(self, winRuleMgr):
        self.__win_rule_mgr = winRuleMgr
    
    def isFriendTablePlaying(self):
        if self.getTableConfig(MFTDefine.IS_CREATE, 0):
            curCount = self.getTableConfig(MFTDefine.CUR_ROUND_COUNT, 0)
            ftlog.debug('MajiangTableLogic.isPlaying friendTable curCount:', curCount
                    , ' totalCount:', self.getTableConfig(MFTDefine.ROUND_COUNT, 0))
            return (curCount > 0) and (curCount != self.getTableConfig(MFTDefine.ROUND_COUNT, 0)) \
                   or self.getTableConfig(MFTDefine.CUR_BASE_COUNT, 0) > 1
        
        return self.isPlaying()
    
    def isPlaying(self):
        """游戏是否开始"""
        if self.__table_win_state == MTableState.TABLE_STATE_NEXT:
            return True
        return False

    def curState(self):
        """当前状态
        """
	state = MTableState.TABLE_STATE_NEXT
        if self.qiangjinProcessor.getState() == MTableState.TABLE_STATE_NEXT and self.__qiangjin:
	    #ftlog.debug('MajiangTableLogic.autoKaijin called 7',self.__qiangjin)
	    state = MTableState.TABLE_STATE_DROP    
        return self.addCardProcessor.getState() \
                + self.tingBeforeAddCardProcessor.getState() \
                + self.tianTingProcessor.getState() \
                + self.__drop_card_processor.getState() \
                + self.__table_win_state \
                + self.__qiang_gang_hu_processor.getState() \
                + self.qiangExmaoPengProcessor.getState() \
                + self.qiangExmaoHuProcessor.getState() \
                + self.__piao_processor.getState() \
                + self.doubleProcessor.getState() \
                + self.louHuProcesssor.getState() \
                + self.absenceProcessor.getState() \
                + self.change3tilesProcessor.getState() \
                + self.daFengProcessor.getState() \
                + self.zhisaiziProcessor.getState()\
                + self.kaijinProcessor.getState()\
		+ self.qiangjinProcessor.getState()\
                + self.flowerProcessor.getState()\
    		+ state
    def nowPlayerCount(self):
        """座位上的人数
        """
        return len(self.__players)
        
    def setTableConfig(self, config):
        """设置牌桌配置"""
        self.__table_config = config

        # 将TableConfig传递到tableTileMgr，方便各种特殊操作的判断
        self.tableTileMgr.setTableConfig(config)
	self.geoMixin.setTableConfig(config)

        cardCount = self.getTableConfig(MTDefine.HAND_COUNT, MTDefine.HAND_COUNT_DEFAULT)
        self.setHandCardCount(cardCount)
 
        if MFTDefine.ROUND_COUNT not in self.__table_config:
            self.__table_config[MFTDefine.ROUND_COUNT] = 0
            
        if MFTDefine.CUR_ROUND_COUNT not in self.__table_config:
            self.__table_config[MFTDefine.CUR_ROUND_COUNT] = 0

        if MFTDefine.BASE_COUNT not in self.__table_config:
            self.__table_config[MFTDefine.BASE_COUNT] = 0

        if MFTDefine.CUR_BASE_COUNT not in self.__table_config:
            self.__table_config[MFTDefine.CUR_BASE_COUNT] = 0

        if MFTDefine.QUAN_COUNT not in self.__table_config:
            self.__table_config[MFTDefine.QUAN_COUNT] = 0
            
        if MFTDefine.CUR_QUAN_COUNT not in self.__table_config:
            self.__table_config[MFTDefine.CUR_QUAN_COUNT] = 0
            
        if MFTDefine.CARD_COUNT not in self.__table_config:
            self.__table_config[MFTDefine.CARD_COUNT] = 0
        
        if MFTDefine.LEFT_CARD_COUNT not in self.__table_config:
            self.__table_config[MFTDefine.LEFT_CARD_COUNT] = 0
            
        if MTDefine.TRUSTTEE_TIMEOUT not in self.__table_config:
            self.__table_config[MTDefine.TRUSTTEE_TIMEOUT] = 1
        
        if self.checkTableState(MTableState.TABLE_STATE_TING):
            self.__ting_rule_mgr.setTableConfig(config)
        
    def getTableConfig(self, key, default):
        """获取牌桌配置"""
        value = self.__table_config.get(key, default)
        return value
        
    @property
    def tableConfig(self):
        return self.__table_config
        
    def queryBanker(self):
        """查询庄家
        """
        return self.bankerMgr.queryBanker()
    
    def calcQuan(self,playerCount, winLoose, winSeatId):
        """计算圈数
        """
        # 圈+1              
        newbanker = self.bankerMgr.calcNextBanker(playerCount, winLoose, winSeatId, {MBanker.GANG_COUNT: self.tableTileMgr.gangCount})
        oldBanker = self.queryBanker()
        if (newbanker != oldBanker) and (newbanker == 0) and self.isCountByQuan():            
            self.tableConfig[MFTDefine.CUR_QUAN_COUNT] += 1
            ftlog.debug('gameWin:CUR_QUAN_COUNT:', self.tableConfig[MFTDefine.CUR_QUAN_COUNT])
        
    def getBankerString(self):
        banker = self.queryBanker()
        switcher = {
        0: "东",
        1: "南",
        2: "西",
        3: "北" }
        
        return switcher.get(banker, "庄")
      
        
    def isThisQuanEnd(self, winLoose):
        """当前圈是否结束
        """
        if not self.isCountByQuan():
            return False
        
        nowBanker = self.queryBanker()
        curRoundCount = self.tableConfig.get(MFTDefine.CUR_ROUND_COUNT, 0)
        nextBanker = self.bankerMgr.calcNextBanker(self.playerCount
                , (curRoundCount == 0)
                , winLoose
                , self.curSeat)
        
        if (nowBanker != nextBanker) and (nowBanker == 0):
            return True
        
        return False
    
    def getPlayerState(self, seatId):
        """获取用户状态"""
        if seatId >= self.__playerCount:
            return None
        
        return self.__players[seatId].state
    
    def getPlayer(self, seatId):
        """获取用户名称"""
        return self.__players[seatId]
    
    def addPlayer(self, player, seatId, isReady = True, isAutoDecide = False):
        """添加玩家"""
        if player in self.__players:
            ftlog.debug( 'already in table...' )
            return
        if seatId >= self.__playerCount:
            ftlog.debug( 'no seat any more...' )
            return
        
        self.__players[seatId] = player
        self.__msg_processor.setPlayers(self.player)
        self.addCardProcessor.setPlayers(self.player)
        self.tingBeforeAddCardProcessor.setPlayers(self.player)
        self.tianTingProcessor.setPlayers(self.player)
        self.__drop_card_processor.setPlayers(self.player)
        self.__qiang_gang_hu_processor.setPlayers(self.player)
        self.qiangExmaoPengProcessor.setPlayers(self.player)
        self.qiangExmaoHuProcessor.setPlayers(self.player)
	self.geoMixin.setPlayer(self.player)
        self.__piao_processor.setPlayers(self.player)
        self.doubleProcessor.setPlayers(self.player)
        self.absenceProcessor.setPlayers(self.player)
        self.change3tilesProcessor.setPlayers(self.player)
        self.qiangjinProcessor.setPlayers(self.player)
	self.flowerProcessor.setPlayers(self.player)
        self.kaijinProcessor.setPlayers(self.player)
	player.setSeatId(seatId)
        player.setAutoDecide(isAutoDecide)

        self.playerReady(seatId, isReady)
                    
    def removePlayer(self, seatId):
        """删除玩家"""
        ftlog.debug('table_logic.removePlayer seatId:', seatId)
        self.__players[seatId] = None
        self.__msg_processor.setPlayers(self.__players)
        if self.isEmpty():
            self.reset()
        
    def isEmpty(self):
        """是否空桌"""
        for player in self.__players:
            if player:
                return False
        return True
        
    def setAutoDecideValue(self, seatId, adValue):
        """设置玩家的托管状态"""
        if self.__players[seatId]:
            if not self.getTableConfig(MFTDefine.IS_CREATE, 0):
                ftlog.debug('MajiangTableLogic.setAutoDecideValue not in createTable Mode')
                self.__players[seatId].setAutoDecide(adValue)
       
    def getBroadCastUIDs(self, filter_id = -1):
        """获取待广播的UID集合，不包括filter_id及机器人
        不需要向机器人发送消息
        """
        uids = []
        for player in self.__players:
            if player and (not player.isRobot()) and (player.userId != filter_id):
                uids.append(player.userId)
        return uids
    
    def getSeats(self):
        seats = [0 for _ in range(self.playerCount)]
        for index,_ in enumerate(seats):
            if self.__players[index]:
                seats[index] = self.__players[index].userId
        return seats
    
    def isGameOver(self):
        """是否已结束"""
        return self.__table_win_state == MTableState.TABLE_STATE_GAME_OVER
    
    def shuffle(self):
        """洗牌
        """
        if len(self.__players) != self.__playerCount:
            ftlog.debug( 'seats error...' )
            return
        
        ftlog.debug('table_logic shuffle win_automatically:', self.tableConfig.get(MTDefine.WIN_AUTOMATICALLY, 0))
        if self.tableConfig.get(MTDefine.WIN_AUTOMATICALLY, 0):
            self.addCardProcessor.setAutoWin(True)
            self.dropCardProcessor.setAutoWin(True)
            self.msgProcessor.setAutoWin(True)
        else:
            self.addCardProcessor.setAutoWin(False)
            self.dropCardProcessor.setAutoWin(False)
            self.msgProcessor.setAutoWin(False)
            
        tiles_no_pao = self.tableConfig.get(MTDefine.TILES_NO_PAO, 0)
        self.tableTileMgr.setHandilaoCount(tiles_no_pao)

        banker = self.bankerMgr.queryBanker()
        # 调整发牌
        if self.tableConfig.get(MTDefine.REMOVE_FENG_ARROW_TILES):
            self.tableTileMgr.setRemoveArrow(1)
            self.tableTileMgr.setRemoveFeng(1)
        else:
            self.tableTileMgr.setRemoveArrow(0)
            self.tableTileMgr.setRemoveFeng(0)
        # 调整发牌
        if self.playMode == 'luosihu-luosihu':
            if not self.tableConfig.get(MTDefine.CHOOSE_ZFB):
                self.tableTileMgr.setRemoveFeng(1)
        elif self.playMode == 'luosihu-xuezhan':
            self.tableTileMgr.setRemoveArrow(1)
            self.tableTileMgr.setRemoveFeng(1)
        elif self.playMode == 'luosihu-ctxuezhan':
            self.tableTileMgr.setRemoveArrow(1)
            self.tableTileMgr.setRemoveFeng(1)

        # 根据需要与规则计算好牌点和初始张数
        # 好牌点1，放在发牌的最前面，table负责将好牌派发给正确的人
        # 手牌张数13
        self.tableTileMgr.shuffle(1, self.__hand_card_count)
        ftlog.debug( 'Round Tiles:', self.tableTileMgr.getTiles(), "len of round", len(self.__table_tile_mgr.getTiles()))
        
        # 发牌
        self.setCurSeat(banker)
	cur_seat = self.curSeat

        for _ in range(self.__playerCount):
            handCards = self.tableTileMgr.popTile(self.__hand_card_count)
            curPlayer = self.__players[cur_seat]
            curPlayer.actionBegin(handCards)
            # 发送发牌的消息
	    ftlog.debug('sendMsgInitTils shuffle')
            self.__msg_processor.sendMsgInitTils(curPlayer.copyHandTiles()
                        , self.bankerMgr.queryBanker()
                        , curPlayer.userId, cur_seat)
            cur_seat = (cur_seat + 1) % self.__playerCount


        """无为玩法，天听特殊处理逻辑，"""
        if self.tableConfig.get(MTDefine.TING_WITH_BEGIN, 0):
            # 天听需要听状态 天听之后取消听状态
            if not self.checkTableState(MTableState.TABLE_STATE_TING):
                self.tableStater.setState(MTableState.TABLE_STATE_TING)
            # 不需要处理庄家
            isTianTing = 0
            for cp in self.player:
                #if self.queryBanker() != cp.curSeatId:
                # 测试当前玩家是否可以听
                canTing, winNodes = self.tingRule.canTingBeforeAddTile(cp.copyTiles()
                                                                       , self.tableTileMgr.tiles
                                                                       ,self.tableTileMgr.getMagicTiles(cp.isTing())
                                                                       , self.__cur_seat
                                                                       , cp.curSeatId
                                                                       , self.actionID)
                ftlog.debug('MajiangTableLogic.shuffle, tian, canTing:', canTing
                            , ' winNodes:', winNodes)
                if canTing:
                    isTianTing = 1
                    self.tianTingProcessor.initProcessor(MTableState.TABLE_STATE_TING, cp.curSeatId, winNodes, 9)
                    winTiles = self.tianTingProcessor.getWinTiles(cp.curSeatId)
                    ftlog.debug('MajiangTableLogic.shuffle tianTingProcessor winTiles:', winTiles)
                    if self.queryBanker() != cp.curSeatId:
                        # 庄家的天听状态要添加 但是不需要发ask_ting
                        self.msgProcessor.table_call_ask_ting(cp.curSeatId, self.actionID, winTiles, [], 9)
            if isTianTing:
                self.msgProcessor.setTianTing(True)
                #self.msgProcessor.table_call_tian_ting(self.__cur_seat, self.actionID, 9)

        """结束"""

        pigus = self.tableTileMgr.getPigus()
        if pigus and len(pigus) > 0:
            uids = self.getBroadCastUIDs()
            self.msgProcessor.table_call_fanpigu(pigus, uids)
        #下发赖子
        magicFactors = self.tableTileMgr.getMagicFactors()
        magicTiles = self.tableTileMgr.getMagicTiles()
        if len(magicFactors) == 0:
            for magicTile in magicTiles:
                if magicTile == MTile.TILE_HONG_ZHONG:
                    magicFactors.append(MTile.TILE_BAI_BAN)
                elif magicTile == MTile.TILE_DONG_FENG:
                     magicFactors.append(MTile.TILE_BEI_FENG)
                elif magicTile%10 == 1:
                    magicFactors.append(magicTile + 8)
                else:
                    magicFactors.append(magicTile - 1)
        if len(magicTiles) > 0:
            self.msgProcessor.table_call_laizi(self.getBroadCastUIDs(), magicTiles, magicFactors)
        
    def checkTableState(self, state):
        """校验牌桌状态机
        """
        return state & self.__table_stater.states
    
    def popOneTile(self, seatId):
        """获取后面的length张牌"""
        tiles = self.tableTileMgr.popTile(1)
        if len(tiles) == 0:
            return None
        else:
            self.tableTileMgr.setAddTileInfo(tiles[0], seatId)
        return tiles[0]
    
    def isFirstAddTile(self, seatId):
        '''
        是本局的第一手牌
        '''
        return len(self.tableTileMgr.dropTiles[seatId]) == 0 #出牌区没有牌
    
    def haveRestTile(self):
        """检查牌堆剩余的牌"""
        restTilesCount = self.tableTileMgr.getCheckFlowCount()
        if restTilesCount <= 0:
            ftlog.debug("haveRestTile no tile left")
            return False
        else:
            return True
         
    def checkBeginHu(self):	#(self, cp, state, tile = 0, addInfo = {}):
        # 检查第一次发牌之后就和牌的情况
	if self.actionID > 1:
            return False,[],0
	if MPlayMode().isSubPlayMode(self.playMode, MPlayMode.QUESHOU):
	    if not self.checkTableState(MTableState.TABLE_STATE_TING):
	        return False,[],0	    
            states = [0 for _ in range(self.playerCount)]
            hasAction = False
	    tile = self.players[self.curSeat].curTile	
    	    exInfo = None
	    state = MTableState.TABLE_STATE_NEXT
            timeOut = self.tableStater.getTimeOutByState(state)
            for player in self.players:
                if player.curSeatId == self.curSeat: 
                    magics = self.tableTileMgr.getMagicTiles(player.isTing())
                    winResult, winPattern,_ = self.__win_rule_mgr.isHu(player.copyTiles(), tile, player.isTing(), MWinRule.WIN_BY_MYSELF, magics, player.winNodes, \
                                                       self.__cur_seat, player.curSeatId, self.actionID)
                    if winResult:
                        states[player.curSeatId] = MTableState.TABLE_STATE_TIANHU
                        hasAction = True

                    magicHuResult = self.__win_rule_mgr.isMagicHu(player.copyTiles(), tile, player.isTing(), MWinRule.WIN_BY_MYSELF, magics, player.winNodes,self.__cur_seat, player.curSeatId, self.actionID)
                    if magicHuResult and not states[player.curSeatId]:
                        states[player.curSeatId] = MTableState.TABLE_STATE_SANJINDAO
                        hasAction = True                    
 
		    tingResult, tingReArr = self.tingRule.canTingForQiangjin(player.copyTiles(), self.tableTileMgr.tiles, tile, self.tableTileMgr.getMagicTiles(player.isTing()),self.__cur_seat, player.curSeatId, self.actionID,True)
                    if tingResult and not states[player.curSeatId]:
                        states[player.curSeatId] = MTableState.TABLE_STATE_QIANGJIN_B
                        hasAction = True
		else:
                    magicHuResult = self.__win_rule_mgr.isMagicHu(player.copyTiles(), tile, player.isTing(), MWinRule.WIN_BY_MYSELF, 	\
				 self.tableTileMgr.getMagicTiles(player.isTing()), player.winNodes,self.__cur_seat, player.curSeatId, self.actionID)
		 
                    if magicHuResult and not states[player.curSeatId]:
                        states[player.curSeatId] = MTableState.TABLE_STATE_SANJINDAO
                        hasAction = True 		    

                    canTing, winNodes = self.tingRule.canTingForQiangjinBeforeAddTile(player.copyTiles(), self.tableTileMgr.tiles, self.tableTileMgr.getMagicTiles(player.isTing()),\
                                                        self.__cur_seat, player.curSeatId,self.actionID)
                    if canTing and not states[player.curSeatId]:
                        states[player.curSeatId] = MTableState.TABLE_STATE_QIANGJIN
                        hasAction = True
	    return hasAction,states,timeOut
	return False,[],0


    def double(self, seatId):
        ftlog.debug('MajiangTableLogic.double seatId:', seatId)
        self.doubleProcessor.double(seatId)
        if self.doubleProcessor.getState() == 0:
            self.beginGame()
            
    def noDouble(self, seatId):
        ftlog.debug('MajiangTableLogic.nodouble seatId:', seatId)
        self.doubleProcessor.noDouble(seatId)
        if self.doubleProcessor.getState() == 0:
            self.beginGame()
    
    def extendMao(self, seatId, extend, maoType):
        if not self.checkTableState(MTableState.TABLE_STATE_FANGMAO):
            ftlog.error('WRONG table action extendMao ...')
            return False
        
        ftlog.debug('MajiangTableLogic.extendMao seatId:', seatId
                    , ' tile:', extend
                    , ' maoType:', maoType)
        if self.addCardProcessor.getState() != 0:
            
            ftlog.debug( 'MajiangTableLogic.extendMao, self.__add_card_processor.getState() != 0')
            # 判断其他玩家是否可以抢锚碰
            # 如果没有玩家抢锚碰，给当前玩家发牌
            # 如果有玩家抢，等待改玩家的抢结果
            canExMao = True
            if self.checkTableState(MTableState.TABLE_STATE_QIANG_EXMAO) \
                or self.checkTableState(MTableState.TABLE_STATE_QIANG_EXMAO_HU) and (not self.tableTileMgr.isHaidilao()):
                ftlog.debug( 'MajiangTableLogic.extendMao, MTableState.TABLE_STATE_QIANG_EXMAO')
                for index in range(1, self.playerCount):
                    newSeatId = (seatId + index) % self.playerCount
                    # 判断是否抢
                    player = self.player[newSeatId]

                    checkTile = extend 
                    pTiles = player.copyTiles()
                    pTiles[MHand.TYPE_HAND].append(checkTile)
                    
                    hasPeng = False
                    hasHu = False
		    winResult = False
                    exInfo = MTableStateExtendInfo()
                    state = MTableState.TABLE_STATE_NEXT
                        
                    if self.checkTableState(MTableState.TABLE_STATE_QIANG_EXMAO):
                        pengSolutions = self.pengRuleMgr.hasPeng(pTiles, checkTile, newSeatId)
                        ftlog.debug( 'MajiangTableLogic.extendMao, pTiles = player.copyTiles()', pTiles
                                     , ' checkTile', checkTile
                                     , ' pengSolutions', pengSolutions)
                        newPengSolutions = []
                        for peng in pengSolutions:
                            if checkTile in peng:
                                canDrop, _ = player.canDropTile(checkTile, self.playMode)
                                if canDrop:
                                    newPengSolutions.append(peng)
                                    break
                        ftlog.debug( 'MajiangTableLogic.extendMao, pTiles = player.copyTiles()', pTiles
                                     , ' checkTile', checkTile
                                     , ' newPengSolutions', newPengSolutions)
                        
   			quemen = -1
                	if self.checkTableState(MTableState.TABLE_STATE_ABSENCE): 
	                    quemen = self.absenceProcessor.absenceColor[player.curSeatId] 
                        gangSolutions = self.gangRuleMgr.hasGang(pTiles, checkTile, MTableState.TABLE_STATE_NEXT,quemen)
                        ftlog.debug( 'MajiangTableLogic.extendMao, pTiles = player.copyTiles()', pTiles
                                     , ' checkTile', checkTile
                                     , ' gangSolutions', gangSolutions)
                        newGangSolutions = []
                        for gang in gangSolutions:
                            # 补锚抢杠只能抢算法里面的暗杠
                            if gang['style'] == MPlayerTileGang.MING_GANG:
                                continue
    
                            if checkTile in gang['pattern']:
                                canDrop, _ = player.canDropTile(checkTile, self.playMode)
                                if canDrop:
                                    gang['style'] = MPlayerTileGang.MING_GANG
                                    newGangSolutions.append(gang)
                                    break
                        ftlog.debug( 'MajiangTableLogic.extendMao, pTiles = player.copyTiles()', pTiles
                                     , ' checkTile', checkTile
                                     , ' newGangSolutions', newGangSolutions)

                        if len(newPengSolutions) > 0:
                            ftlog.debug('MajiangTableLogic.extendMao, qiangPeng')
                            # 可以抢锚碰，给用户选择
                            hasPeng = True
                            state = state | MTableState.TABLE_STATE_PENG
                            exInfo.appendInfo(MTableState.TABLE_STATE_PENG, newPengSolutions[0])
                            ftlog.debug('MajiangTableLogic.extendMao, user:', newSeatId
                                         , ' can peng. extendInfo:', exInfo)
    
                        if len(newGangSolutions) > 0:
                            ftlog.debug('MajiangTableLogic.extendMao, has qiangGang')
                            hasPeng = True
                            state = state | MTableState.TABLE_STATE_GANG
                            exInfo.appendInfo(MTableState.TABLE_STATE_GANG, newGangSolutions[0])
                            ftlog.debug('MajiangTableLogic.extendMao, user:', newSeatId
                                        , ' can Gang. extengInfo:', exInfo)

                        if hasPeng:
                            # 继续检查此人是
                            canExMao = False
                            timeOut = self.tableStater.getTimeOutByState(state)
                            self.addCardProcessor.reset()
                            self.dropCardProcessor.reset()
                            self.qiangGangHuProcessor.reset()
                            self.qiangExmaoPengProcessor.initProcessor(self.actionID
                                    , self.curSeat # 补锚的人
                                    , maoType # 补锚的类型
                                    , newSeatId # 抢锚的人
                                    , state # 抢锚的state
                                    , exInfo # 抢锚人的exInfo
                                    , extend
                                    , timeOut)
                     
                    
                    if self.checkTableState(MTableState.TABLE_STATE_QIANG_EXMAO_HU):       
                        #modify by youjun 04.28
                        if self.checkTableState(MTableState.TABLE_STATE_ABSENCE):
                            absenceColor = self.absenceProcessor.absenceColor[newSeatId]
                            tileArr = MTile.changeTilesToValueArr(self.players[newSeatId].handTiles)
                            if MTile.getTileCountByColor(tileArr, absenceColor) > 0:
                                winResult = False
                            else:
                                winResult, winPattern,_ = self.__win_rule_mgr.isHu(pTiles, checkTile, False, MWinRule.WIN_BY_OTHERS, [], [], self.curSeat, newSeatId, self.actionID, False)
                                ftlog.debug( 'extenMao qianghu, winResutl:', winResult, 'tile',tile, 'winPattern:', winPattern )   
		        #winResult, winPattern = self.__win_rule_mgr.isHu(pTiles, checkTile, False, MWinRule.WIN_BY_OTHERS, [], [], self.curSeat, newSeatId, self.actionID, False)
                        #ftlog.debug( 'extenMao qianghu winResult:', winResult, ' winPattern:', winPattern )
                        
                        if winResult:
                            hasHu = True
                            state = state | MTableState.TABLE_STATE_HU
                            winInfo = {}
                            winInfo['tile'] = checkTile
                            exInfo.appendInfo(state, winInfo)
                        
                        if hasHu:
                            canExMao = False
                            timeOut = self.tableStater.getTimeOutByState(state)
                            self.addCardProcessor.reset()
                            self.dropCardProcessor.reset()
                            self.qiangGangHuProcessor.reset()
                            self.qiangExmaoHuProcessor.initProcessor(self.actionID
                                    , self.curSeat # 补锚的人
                                    , maoType # 补锚的类型
                                    , newSeatId # 抢锚hu的人
                                    , MTableState.TABLE_STATE_QIANG_EXMAO_HU # 抢锚的state
                                    , exInfo # 抢锚人的胡牌exInfo
                                    , extend
                                    , timeOut)

                    if hasPeng or hasHu:    
                        #给玩家发送一个可以碰牌消息
                        message = self.msgProcessor.table_call_drop(self.curSeat
                            , player
                            , checkTile
                            , state
                            , exInfo
                            , self.actionID
                            , timeOut)
                        ftlog.debug( 'MajiangTableLogic.extendMao, table_call_drop: mmessage' ,message)
                        self.msgProcessor.send_message(message, [player.userId])
            
            if canExMao:            
                ftlog.debug( 'MajiangTableLogic.extendMao, self.justExmao(seatId,extend,maoType):' )
                self.justExmao(seatId, extend, maoType)

        ftlog.debug( 'extendMao(self, seatId, extend, maoType) return True')    
        return True
    
    #不用检查抢 直接exmao
    def justExmao(self, seatId, extend, maoType):
        
        ftlog.debug('MTableLogic.justExmao seatId:', seatId, ' extend:', extend, 'maoType:', maoType)

        player = self.player[seatId]
        result, mao = player.actionExtendMao(extend, maoType)
        if not result:
            ftlog.info('table_logic.justExmao error, please check....')
            return False
        
        self.incrActionId('justExmao')
        # 广播补锚消息
        for index in range(self.playerCount):
            self.msgProcessor.table_call_after_extend_mao(self.curSeat, index, mao, self.actionID, self.player[index])
        
        #记录锚杠牌得分
        gangBase = self.getTableConfig(MTDefine.GANG_BASE, 0)
        ftlog.debug('MajiangTableLogic.justExmao gangBase: ', gangBase)
        
        if gangBase > 0:
            result = MOneResultFactory.getOneResult(self.playMode)
            result.setResultType(MOneResult.RESULT_GANG)
            result.setLastSeatId(self.curSeat)
            result.setWinSeatId(self.curSeat)
            result.setTableConfig(self.tableConfig)
            result.setTableTileMgr(self.tableTileMgr)
            # 杠牌算分时，需要找到杠牌时的actionId，杠本身+1，所以此处-1
            result.setActionID(self.actionID - 1)
            result.setPlayerCount(self.playerCount)
            result.setStyle(MPlayerTileGang.EXMao_GANG)
            result.setMultiple(self.__win_rule_mgr.multiple)
            result.setPiaoProcessor(self.piaoProcessor)
            result.calcScore()

            #设置牌局过程中的补锚番型信息
            if result.isResultOK():
                self.roundResult.setPlayMode(self.playMode)
                self.roundResult.addRoundResult(result)
                ftlog.debug('roundResult.addRoundResult 1')
		#加上牌桌上局数总分
                tableScore = [0 for _ in range(self.playerCount)]
                if self.tableResult.score:
                    tableScore = self.tableResult.score
                currentScore = [0 for _ in range(self.playerCount)]
                for i in range(self.playerCount):
                    currentScore[i] = tableScore[i] + self.roundResult.score[i]
                self.msgProcessor.table_call_score(self.getBroadCastUIDs(), currentScore, self.roundResult.delta)

        #补锚之后判断是否换宝
        self.changeMagicTileAfterChiPengExmao()
        
        self.processAddTile(player, MTableState.TABLE_STATE_NEXT)
        return True
 
    def changeMagicTileAfterChiPengExmao(self):
        '''
	if self.playMode == MPlayMode.LUOSIHU:
            changeMagicConfig = self.tableConfig.get(MTDefine.CHANGE_MAGIC, 0)
            if changeMagicConfig:
                bChanged = False
                magics = self.tableTileMgr.getMagicTiles(True)
                while (len(magics) > 0) and (self.tableTileMgr.getVisibleTilesCount(magics[0]) == 3): 
                    if not self.tableTileMgr.updateMagicTile():
                        break
                    
                    bChanged = True
                    magics = self.tableTileMgr.getMagicTiles(True)
    
                if bChanged:
                    # 发送换宝通知
                    self.updateBao()
        '''

    def fangMao(self, seatId, mao):
        '''
            放锚/放蛋
        '''
        if not self.checkTableState(MTableState.TABLE_STATE_FANGMAO):
            ftlog.error('WRONG table action...')
            return False
        
        maoPattern = mao['pattern']
        if len(maoPattern) != 3:
            ftlog.info('table_logic.fangMao card num error!!!')
            return False
        
        maoType = mao['type']
        ftlog.debug('table_logic.fangMao pattern:', maoPattern, ' type:', maoType)
    
        maoDanSetting = self.tableConfig.get(MTDefine.MAO_DAN_SETTING, MTDefine.MAO_DAN_NO)
        if not self.maoRuleMgr.checkMao(maoPattern, maoType, maoDanSetting):
            ftlog.info('table_logic.fangMaos mao:', mao , ' not valid!!!!!')
            return False
    
        ftlog.debug('table_logic.fangMao seatId:', seatId, ' mao:', mao)
        
        cp = self.player[seatId]
        if not cp.actionFangMao(maoPattern, maoType, self.actionID):
            ftlog.info('table_logic.fangMaos, execute fangMao to user error!!! maoPattern:', maoPattern, ' maoType:', maoType, ' actionId:', self.actionID)
            return False
                
        # 增加actionID
        self.incrActionId('fangMao')
        #记录锚杠牌得分
        gangBase = self.getTableConfig(MTDefine.GANG_BASE, 0)
        ftlog.debug('MajiangTableLogic.fangMao gangBase: ', gangBase)
        
        if gangBase > 0:
            result = MOneResultFactory.getOneResult(self.playMode)
            result.setResultType(MOneResult.RESULT_GANG)
            result.setLastSeatId(self.curSeat)
            result.setWinSeatId(self.curSeat)
            result.setTableConfig(self.tableConfig)
            result.setTableTileMgr(self.tableTileMgr)
            # 杠牌算分时，需要找到杠牌时的actionId，杠本身+1，所以此处-1
            result.setActionID(self.actionID - 1)
            result.setPlayerCount(self.playerCount)
            if maoType & MTDefine.MAO_DAN_ZFB:
                result.setStyle(MPlayerTileGang.ZFB_GANG)
            elif (maoType & MTDefine.MAO_DAN_YAO) or (maoType & MTDefine.MAO_DAN_JIU):
                result.setStyle(MPlayerTileGang.YAOJIU_GANG)
                
            result.setMultiple(self.__win_rule_mgr.multiple)
            result.setPiaoProcessor(self.piaoProcessor)
            result.calcScore()

            '''
            jason
            if result.results.get(MOneResult.KEY_GANG_STYLE_SCORE, None):
                ftlog.debug('MajiangTableLogic.fangMao add gang score to cp: ', result.results[MOneResult.KEY_GANG_STYLE_SCORE], ',actionID', self.actionID)
                # 杠牌算分时，需要找到杠牌时的actionId，杠本身+1，所以此处-1
                cp.addGangScore(self.actionID - 1, result.results[MOneResult.KEY_GANG_STYLE_SCORE])
            '''

            #设置牌局过程中的放锚番型信息
            if result.isResultOK():
                self.roundResult.setPlayMode(self.playMode)
                self.roundResult.addRoundResult(result)
                ftlog.debug('roundResult.addRoundResult 2')
		#加上牌桌上局数总分
                tableScore = [0 for _ in range(self.playerCount)]
                if self.tableResult.score:
                    tableScore = self.tableResult.score
                currentScore = [0 for _ in range(self.playerCount)]
                for i in range(self.playerCount):
                    currentScore[i] = tableScore[i] + self.roundResult.score[i]
                self.msgProcessor.table_call_score(self.getBroadCastUIDs(), currentScore, self.roundResult.delta)


        tile = cp.curTile
        if tile not in cp.handTiles:
            tile = cp.handTiles[-1]
        ftlog.debug( 'MajiangTableLogic.fangMaocheck tile:',tile)
        state = MTableState.TABLE_STATE_NEXT
        state, extend = self.calcAddTileExtendInfo(cp, state, tile, {})
 
        timeOut = self.__table_stater.getTimeOutByState(state)
        for index in range(self.__playerCount):
            ftlog.debug( 'MajiangTableLogic.fangMaocheck self.__cur_seat=:', (self.__cur_seat), "index = ", index)
            if self.__cur_seat == index:
                self.__msg_processor.table_call_fang_mao(self.__players[index]
                            , mao
                            , self.player[self.curSeat].copyMaoTile()
                            , state
                            , index
                            , timeOut
                            , self.actionID
                            , extend)
            else:
                self.__msg_processor.table_call_fang_mao_broadcast(self.curSeat
                            , timeOut
                            , self.actionID
                            , self.__players[index].userId
                            , self.player[self.curSeat].copyMaoTile()
                            , mao)
                
        self.changeMagicTileAfterChiPengExmao()
    
    def ifCalcFangDan(self, seatId):
        '''
        是否计算放蛋/锚
        '''
        ftlog.debug('table_logic.ifCalcFangDan seatId:', seatId
                    , ' tileLeft:', self.tableTileMgr.getTilesLeftCount()
                    , ' maoDanSetting:', self.tableConfig.get(MTDefine.MAO_DAN_SETTING, MTDefine.MAO_DAN_NO)
                    , ' fangDanSetting:', self.tableConfig.get(MTDefine.MAO_DAN_FANG_TIME, MTDefine.MAO_DAN_FANG_FIRST_CARD)
                    , ' isFirstAddTile: ', self.isFirstAddTile(seatId))
        
        # 牌堆还有8张牌时，不放锚/蛋，8张未经过具体计算，先加一个范围
        if self.tableTileMgr.getTilesLeftCount() <= 8:
            return False
        
        maoDanSetting = self.tableConfig.get(MTDefine.MAO_DAN_SETTING, MTDefine.MAO_DAN_NO)
        if maoDanSetting == MTDefine.MAO_DAN_NO:
            return False

        return True
    
    def calcAddTileExtendInfo(self, cp, state, tile, addInfo = {}):
        isAfterGang = (state & MTableState.TABLE_STATE_GANG)
        # 从抢杠听转过来听牌的处理需求
        mustTing = (state & MTableState.TABLE_STATE_GRABTING)
        # 扩展数据
        exInfo = MTableStateExtendInfo()
        # 判断和之外的状态，是否可听，可杠
        state = MTableState.TABLE_STATE_NEXT
        
        if self.checkTableState(MTableState.TABLE_STATE_BUFLOWER):
            oneFlowers = self.flowerRuleMgr.hasFlower(cp.copyHandTiles())
            flowers = [[] for _ in range(self.playerCount)]
            flowers[cp.curSeatId] = oneFlowers
            flowerCount = self.flowerRuleMgr.getFlowerCount(flowers)
            if flowerCount > 0:
                if self.tableTileMgr.addTiles[cp.curSeatId]==1 and self.tableTileMgr.buFlowerInFirstTile():
                    isBeginAddTile = True
                else:
                    isBeginAddTile = False
                self.flowerProcessor.initProcessor(MTableState.TABLE_STATE_BUFLOWER, flowers, isBeginAddTile, cp.curSeatId)
                return state, exInfo
        
        # 牌桌变为等待出牌状态
        if (not mustTing) and self.checkTableState(MTableState.TABLE_STATE_DROP):
            state = MTableState.TABLE_STATE_DROP
            
        # 自己上的牌，判断杠/胡，不需要判断吃。判断暗杠
	#modify by youjun 04.28
	#ftlog.debug('calcAddTileExtendInfo about gang state:',self.change3tilesProcessor.getState())
        if self.change3tilesProcessor.getState() == 0 and self.absenceProcessor.getState() == 0:
            if (not mustTing) and self.checkTableState(MTableState.TABLE_STATE_GANG):
                tiles = cp.copyTiles()
                quemen = -1
                if self.checkTableState(MTableState.TABLE_STATE_ABSENCE):
                    quemen = self.absenceProcessor.absenceColor[cp.curSeatId] 
                gangs = self.__gang_rule_mgr.hasGang(tiles, tile, MTableState.TABLE_STATE_NEXT,quemen)
         	#ftlog.debug('calcAddTileExtendInfo gangs=',gangs) 
                if self.checkTableState(MTableState.TABLE_STATE_FANPIGU):
                    pigus = self.tableTileMgr.getPigus()
                    exInfo.appendInfo(MTableState.TABLE_STATE_FANPIGU, pigus)
                
                for gang in gangs:
                    # 可以杠，给用户杠的选择，听牌后，要滤掉影响听口的杠
                    canGang = True
                    if self.playMode == 'luosihu-luosihu' and cp.isTing():
                        if not self.tableConfig.get(MTDefine.GANGWITHTING):
                            canGang = False
                    if canGang and cp.canGang(gang, True, tiles, tile, self.__win_rule_mgr, self.tableTileMgr.getMagicTiles(cp.isTing())):
                        state = state | MTableState.TABLE_STATE_GANG
                        exInfo.appendInfo(MTableState.TABLE_STATE_GANG, gang)

        # 判断听牌, 处于定缺时不做判听
        allTiles = cp.copyTiles()
        if self.checkTableState(MTableState.TABLE_STATE_TING) and self.absenceProcessor.getState() == 0:

            # 没出过牌时摸牌才能的天听
            canTingWithNoDropTile = True
            if self.tableConfig.get(MTDefine.TING_WITH_NO_DROP_TILE, 0) and cp.dropNum > 0:
                canTingWithNoDropTile = False

            # 玩家没有听并且在摸牌之后听的时候，计算听
	    # modify by youjun 05.04
	    if cp.state == MPlayer.PLAYER_STATE_WON and self.checkTableState(MTableState.TABLE_STATE_XUELIU):
		#cp.state = MPlayer.PLAYER_STATE_TING
		ftlog.debug('MajiangTableLogic.processAddTile cp.isTing:',cp.isTing())
            if not cp.isTing() and cp.state != MPlayer.PLAYER_STATE_WON and (self.tableConfig.get(MTDefine.TING_BEFORE_ADD_TILE, 0) == 0) and canTingWithNoDropTile:
                """摸到一张牌，判断是否可以听牌"""
		#begin = datetime.datetime.now()
                tingResult, tingReArr = self.tingRule.canTing(allTiles, self.tableTileMgr.tiles, tile, self.tableTileMgr.getMagicTiles(cp.isTing()), \
                                                              self.__cur_seat, cp.curSeatId, self.actionID)
                #ftlog.debug( 'MajiangTableLogic.processAddTile canTing allTiles=',allTiles,' result: ', tingResult, ' solution:', tingReArr, ' length: ', len(tingReArr) )
		#end = datetime.datetime.now()
		#runTime = end - begin
		#ftlog.debug( 'MajiangTableLogic.processAddTile canTing runTime=',runTime)
                if tingResult and len(tingReArr) > 0:
                    # 可以听牌
                    state = state | MTableState.TABLE_STATE_TING
                    exInfo.appendInfo(MTableState.TABLE_STATE_TING, tingReArr)
                    
        # 判断锚/蛋牌
        if self.checkTableState(MTableState.TABLE_STATE_FANGMAO):
            maoInfo = {}
            if self.ifCalcFangDan(cp.curSeatId) and (not cp.isTing()):
                isFirstAddtile = self.isFirstAddTile(cp.curSeatId)
                maos = self.maoRuleMgr.hasMao(cp.copyHandTiles()
                               , self.tableConfig.get(MTDefine.MAO_DAN_SETTING, MTDefine.MAO_DAN_NO)
                               , cp.getMaoTypes(), isFirstAddtile
							   , {"maoType":cp.getPengMaoTypes()})
                if len(maos) > 0:
                    maoInfo['mao_tiles'] = maos
            
            if not cp.isTing():
                extendMaos = self.maoRuleMgr.hasExtendMao(cp.copyHandTiles(), cp.getMaoTypes())
                if len(extendMaos) > 0:
                    maoInfo['mao_extends'] = extendMaos

            if ('mao_tiles' in maoInfo) or ('mao_extends' in maoInfo):
                state = state | MTableState.TABLE_STATE_FANGMAO
                exInfo.appendInfo(MTableState.TABLE_STATE_FANGMAO, maoInfo)


        # 判断是否自摸和牌
        magics = self.tableTileMgr.getMagicTiles(cp.isTing())
        if self.tableConfig.get(MTDefine.HONG_ZHONG_BAO, 0) and MTile.TILE_HONG_ZHONG not in magics:
            magics.append(MTile.TILE_HONG_ZHONG)
	winResult = False
	magicHuResult = False
	winMode = 0
        if self.absenceProcessor.getState() == 0:  # 不在定缺阶段才做判胡
            #modify by youjun 04.28
            if self.checkTableState(MTableState.TABLE_STATE_ABSENCE):
                absenceColor = self.absenceProcessor.absenceColor[cp.curSeatId]
                tileArr = MTile.changeTilesToValueArr(cp.handTiles)
                if MTile.getTileCountByColor(tileArr, absenceColor) > 0:
                    winResult = False
		else:
		    winResult, winPattern,winMode = self.__win_rule_mgr.isHu(cp.copyTiles(), tile, cp.isTing(), MWinRule.WIN_BY_MYSELF, magics, cp.winNodes, \
                                                      self.__cur_seat, cp.curSeatId, self.actionID, isAfterGang)
            else:
                winResult, winPattern,winMode = self.__win_rule_mgr.isHu(cp.copyTiles(), tile, cp.isTing(), MWinRule.WIN_BY_MYSELF, magics, cp.winNodes, \
                                                       self.__cur_seat, cp.curSeatId, self.actionID, isAfterGang)
		if MPlayMode().isSubPlayMode(self.playMode, MPlayMode.QUESHOU):
                    magicHuResult = self.__win_rule_mgr.isMagicHu(cp.copyTiles(), tile, cp.isTing(), MWinRule.WIN_BY_MYSELF, magics, cp.winNodes,self.__cur_seat, cp.curSeatId, self.actionID, isAfterGang)
                ftlog.debug( 'extenMao qianghu, winResutl:', winResult, 'tile',tile, 'winPattern:', winPattern )  

            if (winResult or magicHuResult) and self.checkTableState(MTableState.TABLE_STATE_HU):
                # 可以和，给用户和的选择
                state = state | MTableState.TABLE_STATE_HU
                winInfo = {}
                winInfo['tile'] = tile
                if isAfterGang:
                    winInfo['gangKai'] = 1
                    if 'lastSeatId' in addInfo:
                        winInfo['lastSeatId'] = addInfo['lastSeatId']
                    if 'seatId' in addInfo:
                        winInfo['seatId'] = addInfo['seatId']
                if addInfo and addInfo.get('buFlower', 0):
                    winInfo['huaCi'] = 1
                winInfo['sanjindao'] = False
		if magicHuResult and winMode <  5:
		    winInfo['sanjindao'] = True
		if MPlayMode().isSubPlayMode(self.playMode, MPlayMode.QUESHOU):
		    winInfo['winMode'] = winMode
                exInfo.appendInfo(MTableState.TABLE_STATE_HU, winInfo)
		ftlog.debug('MajiangTableLogic.calcAddTileExtendInfo winInfo=',winInfo)
        else:  # 记录在定缺，用来在send_tile消息时做判断提示让玩家不能打牌
            exInfo.appendInfo(MTableState.TABLE_STATE_ABSENCE, True)
        # 发牌处理
        ftlog.debug('MajiangTableLogic.processAddTile cp = :', cp.copyHandTiles())
        ftlog.debug('MajiangTableLogic.processAddTile tile:', tile)
        ftlog.debug('MajiangTableLogic.processAddTile extendInfo:', exInfo)

        if self.tableConfig.get(MTDefine.WIN_AUTOMATICALLY, 0) and state & MTableState.TABLE_STATE_HU:
            ftlog.debug('MajiangTableLogic.processAddTile win_auto state old:', state)
            state = MTableState.TABLE_STATE_HU
            ftlog.debug('MajiangTableLogic.processAddTile win_auto state new:', state)

        timeOut = self.__table_stater.getTimeOutByState(state)
        self.addCardProcessor.initProcessor(self.actionID, state, cp.curSeatId, tile, exInfo, timeOut)
        return state, exInfo
    
    def processAddTileSimple(self, cp):
        tile = 0
        if self.haveRestTile():
            tile = self.popOneTile(cp.curSeatId)
        else:
            # 处理流局
            self.gameFlow(cp.curSeatId)
            return
        
        cp.actionAdd(tile)
        #self.incrActionId('addTileSimple')
        state = MTableState.TABLE_STATE_NEXT
        extendInfo = MTableStateExtendInfo()
        # 补花补上来的牌，增加标记isBuFlower
        if self.checkTableState(MTableState.TABLE_STATE_BUFLOWER):
            bustate = MTableState.TABLE_STATE_BUFLOWER
            buInfo = {}
            buInfo['isBuFlowerAddTile'] = 1
            extendInfo.appendInfo(bustate, buInfo)
        self.sendMsgAddTile(state, tile, extendInfo, cp.curSeatId)
        
        
    def processAddTile(self, cp, state, special_tile = None, addInfo = {}):
        """上一张牌并处理
        参数：
            cp - 当前玩家
            tile - 当前上牌
        """
        # 每次在玩家摸牌时，重置其过胡分数
        cp.resetGuoHuPoint()

        tile = 0
        if self.checkTableState(MTableState.TABLE_STATE_FANPIGU) and special_tile:
            tile = special_tile
            self.tableTileMgr.updatePigu(special_tile)
            pigus = self.tableTileMgr.getPigus()
            self.msgProcessor.table_call_fanpigu(pigus, self.getBroadCastUIDs())
        elif self.checkTableState(MTableState.TABLE_STATE_ABSENCE) and special_tile:
            tile = special_tile
        else:
            if self.haveRestTile():
                tile = self.popOneTile(cp.curSeatId)
            else:
                # 处理流局
                self.gameFlow(cp.curSeatId)
            
        if not tile:
            return
        
        cp.actionAdd(tile)

        if special_tile == "laiziGangBuTile":
            cp.setLaiziGangBuTile(tile)
        else:
            cp.setLaiziGangBuTile(0)
        
        # 设置上一手杠状态
        if self.latestGangState != cp.curSeatId:
            ftlog.debug("gangTileclearLatestGangStatebefore = ", self.latestGangState)
            self.setLatestGangState(-1)
            self.__win_rule_mgr.setLastGangSeat(-1)
            ftlog.debug("gangTileclearLatestGangStateafter = ", self.latestGangState)
        
        if self.__win_rule_mgr.isPassHu():
            # 清空之前漏胡的牌
            ftlog.debug("passHuClear", cp.curSeatId)
            self.tableTileMgr.clearPassHuBySeatId(cp.curSeatId)
        
        self.incrActionId('addTile')

        # 曲靖麻将判断四幺鸡,注意在上一步tile加到cp手上以后再调用
        if self.__win_rule_mgr.isAddHu(cp, tile):
            state = MTableState.TABLE_STATE_HU
            exInfo = MTableStateExtendInfo() 
            timeOut = self.__table_stater.getTimeOutByState(state)
            self.addCardProcessor.initProcessor(self.actionID, state, cp.curSeatId, tile, exInfo, timeOut)
            #直接胡牌
            self.gameWin(cp.curSeatId, tile)
            return
        
        #判断刮大风情况
        if self.tableConfig.get(MTDefine.GUA_DA_FENG, 0) and cp.isTing():
            if MDaFengRuleBase.canWinByDaFeng(cp, tile, self.gangRuleMgr, self.winRuleMgr, self.tableTileMgr):
                state = MTableState.TABLE_STATE_HU
                exInfo = MTableStateExtendInfo() 
                winInfo = {}
                winInfo['tile'] = tile
                winInfo['daFeng'] = 1
                exInfo.appendInfo(state, winInfo)
                timeOut = self.__table_stater.getTimeOutByState(state)
                self.daFengProcessor.initProcessor(self.actionID, cp.curSeatId, state, tile, exInfo, timeOut)
                self.sendMsgAddTile(state, tile, exInfo, self.curSeat)
                return

        isAfterGang = (state & MTableState.TABLE_STATE_GANG)
        state, exInfo = self.calcAddTileExtendInfo(cp, state, tile, addInfo)
        if self.tableTileMgr.isHaidilao():
            # 海底捞只判断是否自摸
            state = state & MTableState.TABLE_STATE_HU
            if state > 0:
                newExInfo = MTableStateExtendInfo()
                if MTableStateExtendInfo.WIN in exInfo.extend:
                    newExInfo.appendInfo(MTableState.TABLE_STATE_HU, exInfo.extend[MTableStateExtendInfo.WIN][0])
                exInfo = newExInfo
            else:
                exInfo = MTableStateExtendInfo()

	if not self.actionID > 1 and MPlayMode().isSubPlayMode(self.playMode, MPlayMode.QUESHOU):
            exInfo = MTableStateExtendInfo()
            state = MTableState.TABLE_STATE_NEXT
        self.sendMsgAddTile(state, tile, exInfo, self.curSeat)
        
        if isAfterGang and not (state & MTableState.TABLE_STATE_GANG) and \
                not (state & MTableState.TABLE_STATE_TING) and self.tianTingProcessor.getState() != 0:
            # 判断天听 有杠有听 杠完不可听或者连续杠的情况 需要重置天听状态
            ftlog.debug('addTile isAfterGang tianting...')
            if self.tianTingProcessor.updateProcessor(cp.curSeatId):
                if self.tianTingProcessor.getState() == 0:
                    for player in self.player:
                        if player.curSeatId == self.queryBanker():
                            self.msgProcessor.table_call_tian_ting_over(player.curSeatId, self.actionID)

        if (self.tableTileMgr.getCheckFlowCount() - self.tableTileMgr.getFlowCount()) == 8:
            self.msgProcessor.table_call_last_eight_broadcast(self.getBroadCastUIDs())

        if not (state & MTableState.TABLE_STATE_HU or state & MTableState.TABLE_STATE_GANG):
            noDropCardCount = self.tableTileMgr.getTilesNoDropCount()
            if (self.tableTileMgr.getCheckFlowCount() - self.tableTileMgr.getFlowCount()) < noDropCardCount :
                ftlog.info('table_logic.processAddTile calcAddTileExtendInfo getCheckFlowCount:', self.tableTileMgr.getCheckFlowCount()
                            , ' __cur_seat:', self.__cur_seat)
                #剩余四张牌 只摸不打
		self.msgProcessor.table_call_last_round_broadcast(self.getBroadCastUIDs())
                nextSeat = self.nextSeatId(self.__cur_seat)
                self.__cur_seat = nextSeat
                self.processAddTile(self.player[nextSeat], MTableState.TABLE_STATE_NEXT)
        if state & MTableState.TABLE_STATE_HU and self.__win_rule_mgr.canDirectHuAfterTing() and cp.isTing():
            self.gameWin(cp.curSeatId, tile)
            return

        if state & MTableState.TABLE_STATE_HU:
            noDropCardCount = self.tableTileMgr.getTilesNoDropCount()
            if (self.tableTileMgr.getCheckFlowCount() - self.tableTileMgr.getFlowCount()) < noDropCardCount :
                self.gameWin(cp.curSeatId, tile)
                return 
        
    def sendMsgAddTile(self, state, tile, exInfo, curSeat):
        timeOut = self.tableStater.getTimeOutByState(state)
        for index in range(self.playerCount):
            if curSeat == index:
                self.msgProcessor.table_call_add_card(self.players[index]
                            , tile, state, index
                            , timeOut
                            , self.actionID
                            , exInfo
                            , self.getBroadCastUIDs())
            else:
                self.msgProcessor.table_call_add_card_broadcast(self.curSeat
                            , timeOut
                            , self.actionID
                            , self.players[index].userId
                            , tile
			    , self.isSeenTiles())


    def getCreateTableInfo(self, isTableInfo = False):
        """获取自建桌信息"""
        if self.tableType != MTDefine.TABLE_TYPE_CREATE:
            return None
        
        ctInfo = None        
        cFinal = 0
        currentBase = 0
        curCount = self.tableConfig[MFTDefine.CUR_ROUND_COUNT]
        if isTableInfo and (self.__table_win_state != MTableState.TABLE_STATE_NEXT):
            curCount += 1
        totalCount = self.tableConfig[MFTDefine.ROUND_COUNT]
        if curCount >= totalCount:
            curCount = totalCount
            
        if self.isCountByRound(): 
            if (totalCount == curCount) :
                cFinal = 1
        elif self.isCountByQuan():
            if self.tableConfig[MFTDefine.CUR_QUAN_COUNT] == self.tableConfig[MFTDefine.QUAN_COUNT]:
                cFinal = 1
                clientShowQuan = self.tableConfig[MFTDefine.CUR_QUAN_COUNT]
            else:
                clientShowQuan = self.tableConfig[MFTDefine.CUR_QUAN_COUNT]+1
        elif self.tableConfig.get(MTDefine.OVER_BY_SCORE, 0):
            if self.isPlayerFinal():
                cFinal = 1

            currentBase = self.tableConfig[MFTDefine.CUR_BASE_COUNT]
            currentBase = currentBase if currentBase!=0 else currentBase+1
        
        if self.getTableConfig(MFTDefine.QUAN_COUNT, 0)==0:
            currentProgress = '%s/%s局' % (curCount,totalCount)
        else:
            currentProgress = '%s/%s圈-%s' % ( clientShowQuan, self.tableConfig[MFTDefine.QUAN_COUNT],self.getBankerString())        
        
            
        if self.tableConfig.get(MFTDefine.IS_CREATE, 0):
            ctInfo = {"create_table_no": self.getTableConfig(MFTDefine.FTID, '000000'),
                "time": pktimestamp.getCurrentTimestamp(),
                "create_final": cFinal,
                "create_now_cardcount": curCount,
                "create_total_cardcount": totalCount,
                "currentProgress": currentProgress,
                "currentBase": currentBase,
                "itemParams": self.getTableConfig(MFTDefine.ITEMPARAMS, {}),
                "hostUserId": self.getTableConfig(MFTDefine.FTOWNER, 0),
                'create_table_desc_list': self.getTableConfig(MFTDefine.CREATE_TABLE_DESCS, []),
                'create_table_option_name_list': self.getTableConfig(MFTDefine.CREATE_TABLE_OPTION_NAMES, []),
                'create_table_play_desc_list': self.getTableConfig(MFTDefine.CREATE_TABLE_PLAY_DESCS, []),
                'isBaoPaiShow': not self.getTableConfig(MTDefine.MAGIC_HIDE, 0),
                'voteHost': self.voteHost, # -1表示没人解散牌桌，0-3表示对应座位号的人解散牌桌
            }
            ftlog.info('MajiangTableLogic.getCreateTableInfo ctInfo:', ctInfo)
            
        return ctInfo
    
    def getCreateTableRecordName(self):
        """获取牌桌记录信息"""
        if self.runMode == MRunMode.CONSOLE:
            return 'console.json'
        
        curCount = self.getTableConfig(MFTDefine.CUR_ROUND_COUNT, 1)
        totalCount = self.getTableConfig(MFTDefine.ROUND_COUNT, 1)
        recordName = '%s-%s-%d-%d-%d' % (self.playMode, self.getTableConfig(MFTDefine.FTID, '000000'), curCount, totalCount, pktimestamp.getCurrentTimestamp())    
        ftlog.debug('MajiangTableLogic.getCreateTableRecordName recordName:', recordName)
        return recordName
    
    # 大结算时需要返回给客户端的统计信息
    def getCreateExtendBudgets(self):
        createExtendBudgets = [{} for _ in range(self.playerCount)]
        # roundResult 列表
        allResults = []
        tableResults = self.__table_result.results
        ftlog.debug('MajiangTableLogic.getCreateExtendBudgets roundResult count', len(tableResults),tableResults)
        for roundResult in self.__table_result.results:
            ftlog.debug('MajiangTableLogic.getCreateExtendBudgets roundResult ...',roundResult)
            for oneResult in roundResult.roundResults:
            	allResults.append(oneResult)
            	ftlog.debug('MajiangTableLogic.getCreateExtendBudgets oneResult ...',oneResult)
        
        ziMoMaxValue = 0
        ziMoMaxSeatId = -1
        dianPaoMaxValue = 0
        dianPaoMaxSeatId = -1
        #大赢家
	maxScoreData = {'seatId': -1, 'score': -1}
        self.setBiggestWinner(0)
        for seatId in range(self.playerCount):
            extendBudget = {}
            extendBudget["sid"] = seatId
            winValue = 0
            ziMoValue = 0
            moBaoValue = 0
            dianPaoValue = 0
            gangValue = 0
            mingGangValue = 0
            anGangValue = 0
            zuidaFanValue = 0
            bankerValue = 0
            jiaopaiValue = 0
            moziValue = 0  # 摸子分
            pingnaValue = 0  # 平拿分
            qingnaValue = 0  # 清拿分
            #statistics
            statisticInfo = []
            #晃晃喜相逢的次数
            xiXiangFengValue = 0
            # one result
            for oneResult in allResults:
                ftlog.debug('MajiangTableLogic.getCreateExtendBudgets seatId:', seatId)
                #statScore = oneResult.results[MOneResult.KEY_SCORE]
                #totalDeltaScore += statScore[seatId]
                stats = [[] for _ in range(self.__playerCount)]
                playerStats = []
                if MOneResult.KEY_STAT in oneResult.results:
                    stats = oneResult.results[MOneResult.KEY_STAT]
                    playerStats = stats[seatId]
                for stat in playerStats:
                    if MOneResult.STAT_WIN in stat:
                        winValue += stat[MOneResult.STAT_WIN]
                        
                    if MOneResult.STAT_ZIMO in stat:
                        ziMoValue += stat[MOneResult.STAT_ZIMO]
                        
                    if MOneResult.STAT_MOBAO in stat:
                        moBaoValue += stat[MOneResult.STAT_MOBAO]
                    
                    if MOneResult.STAT_DIANPAO in stat:
                        dianPaoValue += stat[MOneResult.STAT_DIANPAO]
                    ftlog.debug('MajiangTableLogic.getCreateExtendBudgets Test winValue:',winValue,' ziMoValue:',ziMoValue,' moBaoValue:',moBaoValue,' dianPaoValue:',dianPaoValue)        

		    if MPlayMode().isSubPlayMode(self.playMode, MPlayMode.LUOSIHU) or MPlayMode().isSubPlayMode(self.playMode, MPlayMode.QUESHOU):
                        if MOneResult.STAT_MINGGANG in stat:
                            mingGangValue += stat[MOneResult.STAT_MINGGANG]
                            
                        if MOneResult.STAT_ANGANG in stat:
                            anGangValue += stat[MOneResult.STAT_ANGANG]
                            
                        if MOneResult.STAT_GANG in stat:
                            gangValue += stat[MOneResult.STAT_GANG]
                            
                    if MOneResult.STAT_ZUIDAFAN in stat:
                        if stat[MOneResult.STAT_ZUIDAFAN] > zuidaFanValue:
                            zuidaFanValue = stat[MOneResult.STAT_ZUIDAFAN]

                    if MOneResult.STAT_BANKER in stat:
                        bankerValue += stat[MOneResult.STAT_BANKER]

                    if MOneResult.STAT_JIAOPAI in stat:
                        jiaopaiValue += stat[MOneResult.STAT_JIAOPAI]

                    if MOneResult.STAT_PINGNA in stat:
                        pingnaValue += stat[MOneResult.STAT_PINGNA]

                    if MOneResult.STAT_QINGNA in stat:
                        qingnaValue += stat[MOneResult.STAT_QINGNA]

                    if MOneResult.STAT_MOZI in stat:
                        moziValue += stat[MOneResult.STAT_MOZI]

                    if MOneResult.STAT_QINGNA in stat:
                        qingnaValue += stat[MOneResult.STAT_QINGNA]

                    if MOneResult.STAT_PINGNA in stat:
                        pingnaValue += stat[MOneResult.STAT_PINGNA]

                    if "xiXiangFeng" in stat:
                        xiXiangFengValue += stat["xiXiangFeng"]
		    ftlog.debug('MajiangTableLogic.getCreateExtendBudgets Test 2  winValue:',winValue,' ziMoValue:',ziMoValue,' moBaoValue:',moBaoValue,' dianPaoValue:',dianPaoValue)
            oneResultForName = MOneResult()
	    statisticInfo.append({"desc":oneResultForName.statType[MOneResult.STAT_ZIMO]["name"],"value":ziMoValue})
            ftlog.debug('MTableLogic.createExtendBudgets seatId', seatId,' ziMoValue:', ziMoValue) 

            if MPlayMode().isSubPlayMode(self.playMode, MPlayMode.LUOSIHU) or MPlayMode().isSubPlayMode(self.playMode, MPlayMode.QUESHOU):
                statisticInfo.append({"desc":oneResultForName.statType[MOneResult.STAT_MINGGANG]["name"],"value":mingGangValue})
                ftlog.debug('MTableLogic.createExtendBudgets seatId', seatId,' mingGangValue:', mingGangValue)
                statisticInfo.append({"desc":oneResultForName.statType[MOneResult.STAT_ANGANG]["name"],"value":anGangValue})
                ftlog.debug('MTableLogic.createExtendBudgets seatId', seatId,' anGangValue:', anGangValue)
            
            statisticInfo.append({"desc":oneResultForName.statType[MOneResult.STAT_DIANPAO]["name"],"value":dianPaoValue})
            ftlog.debug('MTableLogic.createExtendBudgets seatId', seatId,' dianPaoValue:', dianPaoValue)

	    statisticInfo.append({"desc":oneResultForName.statType[MOneResult.STAT_ZUIDAFAN]["name"],"value":zuidaFanValue})
            ftlog.debug('MTableLogic.createExtendBudgets seatId', seatId,' zuidaFanValue:', zuidaFanValue)

            #extendBudget["total_delta_score"] = totalDeltaScore
            if self.__table_result.score and (len(self.__table_result.score) > seatId):
                extendBudget["total_delta_score"] = self.__table_result.score[seatId]
            else:
                extendBudget["total_delta_score"] = 0
            #循环获取最大值，第一个最大值
            if extendBudget["total_delta_score"] > maxScoreData['score']:
                maxScoreData['score'] = extendBudget["total_delta_score"]
                maxScoreData['seatId'] = seatId
            extendBudget["statistics"] = statisticInfo
            # dianpao_most zimo_most
            extendBudget["head_mark"] = ""

            createExtendBudgets[seatId] = extendBudget
            if ziMoValue > ziMoMaxValue:
                ziMoMaxValue = ziMoValue
                ziMoMaxSeatId = seatId
            if dianPaoValue > dianPaoMaxValue:
                dianPaoMaxValue = dianPaoValue
                dianPaoMaxSeatId = seatId

        if ziMoMaxSeatId >= 0:
            createExtendBudgets[ziMoMaxSeatId]["head_mark"] = "zimo_most"
        if dianPaoMaxSeatId >= 0:
            createExtendBudgets[dianPaoMaxSeatId]["head_mark"] = "dianpao_most"

        # 返回玩家每局的分数 (江西，安徽麻将需求）
        if self.tableConfig.get(MFTDefine.BUDGET_INCLUDE_ROUND_SCORE, 0):
            roundNum = len(self.__table_result.results)
            for seatId in xrange(self.playerCount):
                createExtendBudgets[seatId]['delta_scores'] = [0] * roundNum
                for i, roundResult in enumerate(self.__table_result.results):
                    createExtendBudgets[seatId]['delta_scores'][i] = roundResult.score[seatId]
 	ftlog.debug('MajiangTableLogic.getCreateExtendBudgets createExtendBudgets:',createExtendBudgets)
        #大赢家
	if maxScoreData['seatId'] >= 0:
            for p in self.player:
                if p and p.curSeatId == maxScoreData['seatId']:
                    self.setBiggestWinner(p.userId)
        return createExtendBudgets
    
    def winsPayFangKa(self):
        if not self.__table_result.score:
            return 
        maxScore=max(self.__table_result.score)
        winsMax=[]
        hostId=self.tableConfig.get(MFTDefine.FTOWNER,None)
        roomId=self.roomId
        gameId=self.gameId
        tableId=self.tableId

        count=self.tableConfig.get(MFTDefine.CARD_COUNT,1)
        itemId = self.msgProcessor.roomConf.get('create_item', None)
        bigRoomId=self.bigRoomId
        for seat in xrange(self.playerCount):
            if self.__table_result.score[seat]==maxScore:
                winsMax.append(seat)
        user_remote.resumeItemFromTable(hostId, gameId, itemId, count, roomId, tableId, bigRoomId)
        baseFangKaCount=count/len(winsMax)
        for seatId in winsMax:
            userId=self.player[seatId].userId  
            result= user_remote.consumeItem(userId, gameId, itemId, baseFangKaCount, roomId, bigRoomId)
        ftlog.debug('winsFangka:',tableId,count,itemId,result,bigRoomId,winsMax)

    def sendCreateExtendBudgetsInfo(self, terminate):
        if self.tableType != MTDefine.TABLE_TYPE_CREATE:
            return

        #add by taoxc 本桌牌局结束进行大结算
        cebInfo = self.getCreateExtendBudgets()
        # 结算，局数不加1
        ctInfo = self.getCreateTableInfo(False)

        ftlog.debug('table_logic.shuffle cebInfo:', cebInfo)
        self.__msg_processor.table_call_game_all_stat(terminate, cebInfo, ctInfo)
        if self.voteFinal == True:
            recordName = self.getCreateTableRecordName()
            recordUrl = self.msgProcessor.saveRecord(recordName)
            self.__record_url.append(recordUrl)
        # 如果是牌局打完了结算,检查配置付房卡 模式
        if self.playMode == 'luosihu-ctxuezhan' and (self.tableConfig[MFTDefine.CUR_ROUND_COUNT] == self.tableConfig[MFTDefine.ROUND_COUNT]) and self.isGameOver():
            ftlog.info("check self.getFangkaPayConfig in BudgetsInfo")
            if self.getFangkaPayConfig() == 1:
                # 如果房主不是大赢家,归还剩余房卡道具,然后扣除大赢家的房卡
                bWinner = self.biggestWinner
                ftlog.info("MajiangFriendTable.sendCreateExtendBudgetsInfo self.biggestWinner:", self.biggestWinner
                           , "self.tableConfig[MFTDefine.FTOWNER]", self.tableConfig[MFTDefine.FTOWNER])
                if self.tableConfig[MFTDefine.FTOWNER] != bWinner and bWinner > 10000:
                    itemId = self.msgProcessor.roomConf.get('create_item', None)
		    if itemId:
                        #if not self.tableConfig[MFTDefine.ISFREE]:
			if 1==1:
                            if self.tableConfig[MFTDefine.CARD_COUNT] > 0:
                                self.winsPayFangKa()
                        else:
			     ftlog.info("MajiangFriendTable.sendCreateExtendBudgetsInfo,check card info free")	
                    else:
                        ftlog.info("InvalidItem.roomConf", self.msgProcessor.roomConf)
          
    def calcBeginBanker(self):
        curRoundCount = self.tableConfig.get(MFTDefine.CUR_ROUND_COUNT, 0)
        ftlog.debug('table_logic.shuffle curRoundCount:', curRoundCount)
        if 0 == curRoundCount:
            self.bankerMgr.getBanker(self.__playerCount
                , True
                , 0
                , 0)
       
    def sendMsgTableInfo(self, seatId, isReconnect = False):
        """重连"""
        ftlog.info('MajiangTableLogic.sendMsgTableInfo seatId:', seatId, ' isReconnect:', isReconnect)
        if not self.__players[seatId]:
            ftlog.error('MajiangTableLogic.sendMsgTableInfo player info err:', self.__players)

        deltaScore = [0 for _ in range(self.playerCount)]
        allScore = [0 for _ in range(self.playerCount)]
        if isReconnect:
            ftlog.debug('MajiangTableLogic.sendMsgTableInfo actionId:',self.actionID)
	    self.msgProcessor.setActionId(self.actionID)
            #刷新一次当前分数
            tableScore = [0 for _ in range(self.playerCount)]
            if self.tableResult and self.tableResult.score:
                tableScore = self.tableResult.score
            roundScore = [0 for _ in range(self.playerCount)]
            if self.roundResult and self.roundResult.score:
                roundScore = self.roundResult.score
            for i in range(self.playerCount):
                allScore[i] = tableScore[i] + roundScore[i]
            #self.__msg_processor.table_call_score(self.getBroadCastUIDs(), allScore, deltaScore)
            # 如果是重连,在血战模式下需要取到已胡牌人的信息
            #modify by youjun 04.25
	    if self.checkTableState(MTableState.TABLE_STATE_XUEZHAN):
            #    hasHuData = self.__win_rule_mgr.getHasHuData()
	   	ftlog.debug('modify by youjun 04.25')
            #modify end
        # 给玩家设置底分
        baseCount = self.tableConfig.get(MFTDefine.BASE_COUNT, 0)
        allJiaoScore = [0 for _ in range(self.playerCount)]
        if self.tableConfig.get(MTDefine.OVER_BY_SCORE, 0) and baseCount > 0 :
            for player in self.player:
                if not player:
                    continue

                if player.curScore == None:
                    player.initScores(self.tableConfig.get(MFTDefine.INIT_SCORE, 0), baseCount)

                curBaseCount = self.tableConfig.get(MFTDefine.CUR_BASE_COUNT, 0) or 1
                allScore[player.curSeatId] = player.getCurScoreByBaseCount(curBaseCount)
                allJiaoScore[player.curSeatId] = player.getCurJiaoScoreByBaseCount(curBaseCount)

                ftlog.debug('MajiangTableLogic.sendMsgTableInfo baseCount:', baseCount,
                            'curBaseCount',curBaseCount,
                            'allScore', allScore,
                            'allJiaoScore',allJiaoScore)

        ctInfo = self.getCreateTableInfo(True)
        btInfo, atInfo = self.getBaoPaiInfo()
        if self.tableConfig.get(MTDefine.MAGIC_HIDE, 1):
            btInfo = None
        if self.checkTableState(MTableState.TABLE_STATE_TING):
            # 有听牌状态的产品，玩家没有听牌时，不显示宝牌
            if not self.player[seatId].isTing():
                btInfo = None
        
        self.msgProcessor.table_call_table_info(self.players[seatId].userId
                , self.bankerMgr.queryBanker()
                , seatId
                , isReconnect
                , 1
                , self.curSeat
                , 'play'
                , ctInfo
                , btInfo
		, self.bankerMgr.bankerRemainCount)
        if isReconnect:
            self.msgProcessor.table_call_score(self.getBroadCastUIDs(), allScore, deltaScore, allJiaoScore)
            
        self.playerOnline(seatId)
        self.sendPlayerLeaveMsg(self.players[seatId].userId)
            
        # 补发宝牌消息
        if ((not btInfo) or (len(btInfo) == 0)) and ((not atInfo) or (len(atInfo) == 0)):
            return
        
        self.msgProcessor.table_call_baopai(self.player[seatId], btInfo, atInfo)

    def playerReady(self, seatId, isReady):
        """玩家准备"""
        ftlog.info('MajiangTableLogic.playerReady seatId:', seatId, ' isReady:', isReady, ' tableState:', self.__table_win_state,'player:',self.player)
        if seatId < 0:
            return False
        
        if seatId == 0:
            self.refixTableStateByConfig()
            self.refixTableMultipleByConfig()

        if self.__table_win_state == MTableState.TABLE_STATE_NONE or self.__table_win_state == MTableState.TABLE_STATE_GAME_OVER:
            if isReady:
                self.player[seatId].ready()
            else:
                self.player[seatId].wait()
            
            already = self.isAllPlayersReady()
            if already:
                self.playGameByState(self.tableStater.getStandUpSchedule(MTableState.TABLE_STATE_NONE))

            return already

    def playGameByState(self, state):
        ftlog.debug('MajiangTableLogic.playGameByState state:', state)

        if state == MTableState.TABLE_STATE_SAIZI:
            self.zhisaiziProcessor.initProcessor(MTableState.TABLE_STATE_SAIZI
                            , 3
                            , self.bankerMgr
                            , self.msgProcessor
                            , self.getBroadCastUIDs())
        elif state == MTableState.TABLE_STATE_NEXT:
            self.beginGame()
        elif state == MTableState.TABLE_STATE_PIAO:
            self.piaoProcessor.reset()
            self.piaoSchedule()
        elif state == MTableState.TABLE_STATE_DOUBLE:
            self.doubleSchedule()

    def change3tilesSchedule(self):
        self.change3tilesProcessor.setMsgProcessor(self.msgProcessor)
        self.change3tilesProcessor.beginChange3Tiles()
	ftlog.debug('change3tilesSchedule begin')

    def qiangjinSchedule(self,states, actionId, timeOut=0):
    	self.qiangjinProcessor.reset()
	self.qiangjinProcessor.setMsgProcessor(self.msgProcessor)
        self.qiangjinProcessor.beginQiangjin(states, actionId, timeOut)

    def absenceSchedule(self):
        self.absenceProcessor.setMsgProcessor(self.msgProcessor)
        self.absenceProcessor.beginAbsence()

    def doubleSchedule(self):
        self.doubleProcessor.setMsgProcessor(self.msgProcessor)
        self.doubleProcessor.beginDouble(self.actionID, self.tableConfig.get(MTDefine.DOUBLE_TIMEOUT, 9))
        
    def piaoSchedule(self):
        self.piaoProcessor.setBiPiaoPoint(self.tableConfig.get(MTDefine.BIPIAO_POINT, 0))
        self.piaoProcessor.setSchedule(MPiaoProcessor.SCHEDULE_PIAO_ORNOT)
        self.piaoProcessor.setPiaoTimeOut(self.tableConfig.get(MTDefine.PIAO_ORNOT_TIMEOUT, 5))
        self.piaoProcessor.setAcceptPiaoTimeOut(self.tableConfig.get(MTDefine.ACCEPT_PIAO_ORNOT_TIMEOUT, 5))
        self.piaoProcessor.setShowPiaoTimeOut(2)
        piaoList = self.tableConfig.get(MTDefine.PIAO_LIST, [1, 3, 5])
        self.piaoProcessor.beginPiao(self.msgProcessor, piaoList)
        
    def autoDecidePiao(self, seatId):
        if 0 == self.piaoProcessor.getState():
            return
        
        self.piaoProcessor.autoDecide(seatId, self.msgProcessor)
        self.checkPiaoOver()
        self.checkShowPiaoOver()

    def autoDecideDouble(self, seatId):
        if 0 == self.doubleProcessor.getState():
            return
        
        ftlog.debug('table_logic.autoDecideDouble seatId:', seatId, ' noDouble...')
        if self.players[seatId].userId < 10000:
            self.doubleProcessor.noDouble(seatId)
        else:
            self.doubleProcessor.keepNoChange(seatId)
            
        if self.doubleProcessor.getState() == 0:
            self.playGameByState(self.tableStater.getStandUpSchedule(MTableState.TABLE_STATE_DOUBLE))

    def autoDecideCrapShoot(self):
        self.playGameByState(self.tableStater.getStandUpSchedule(MTableState.TABLE_STATE_SAIZI))
        
    def piao(self, seatId, piaoPoint):
        if 0 == self.piaoProcessor.getState():
            return
        self.piaoProcessor.piao(seatId, piaoPoint, self.msgProcessor)
        self.checkPiaoOver()
        
    def acceptPiao(self, seatId, piaoSirId, acceptOrNot):
        ftlog.debug('table_logic.acceptPiao seatId:', seatId
                    , ' piaoSeatId:', piaoSirId
                    , ' acceptOrNot', acceptOrNot)
        if 0 == self.piaoProcessor.getState():
            return
        self.piaoProcessor.acceptPiao(seatId, piaoSirId, acceptOrNot, self.msgProcessor)
        self.checkPiaoOver()
            
    def checkPiaoOver(self):
        ftlog.debug('table_logic checkPiaoOver')
        if self.piaoProcessor.isAllAcceptPiao():
            self.piaoProcessor.setAcceptPiaoTimeOut(0)
            self.piaoProcessor.broadCastPiao(self.msgProcessor)
            self.playGameByState(self.tableStater.getStandUpSchedule(MTableState.TABLE_STATE_PIAO))

    def checkShowPiaoOver(self):
	'''
        if self.piaoProcessor.updateShowPiao():
            self.playGameByState(self.tableStater.getStandUpSchedule(MTableState.TABLE_STATE_PIAO))
        '''
	ftlog.debug('table_logic.checkShowPiaoOver')

    def isAllPlayersReady(self):
        already = True
        for seat in range(self.__playerCount):
            if (self.__players[seat] == None) or (self.__players[seat].state != MPlayer.PLAYER_STATE_READY):
                ftlog.debug( 'Seat:', seat, ' nor ready....' )
                already = False
                break
        
        if not already:
            ftlog.debug( 'MajiangTableLogic.beginGame, all players not ready, begin game later....' )
            return False
        
        # 初始化本局结果
        self.__round_result = MRoundResults()
        self.tableConfig[MTDefine.TABLE_ROUND_ID] = self.getRoundId()
        self.tableConfig[MFTDefine.CUR_ROUND_COUNT] += 1
	#特别逻辑，连庄增加总局数 连 江 modified by robin
        ftlog.debug( 'MajiangTableLogic get bankerMgr remain_count:',self.bankerMgr.remain_count,self.tableConfig[MTDefine.TABLE_ROUND_ID],self.tableConfig[MFTDefine.CUR_ROUND_COUNT])
        if self.bankerMgr.remain_count >0 and self.getTableConfig(MTDefine.LIANZHUANGJIAJU,0):
            self.tableConfig[MFTDefine.ROUND_COUNT] += 1
	    self.msgProcessor.table_call_tableInfo_broadcast(self.getBroadCastUIDs(),self.tableConfig[MFTDefine.CUR_ROUND_COUNT],self.tableConfig[MFTDefine.ROUND_COUNT])
        if self.tableConfig[MFTDefine.CUR_ROUND_COUNT] % 2 == 0 and self.tableConfig[MFTDefine.LEFT_CARD_COUNT] > 0:
            self.tableConfig[MFTDefine.LEFT_CARD_COUNT] -= 1
            ftlog.debug('MajiangTableLogic.beginGame consum card left card count:', self.tableConfig[MFTDefine.LEFT_CARD_COUNT])
        self.__round_result.setRoundIndex(self.tableConfig.get(MFTDefine.CUR_ROUND_COUNT, 0))

        if self.tableConfig.get(MTDefine.OVER_BY_SCORE, 0):
            # 底数判断 如果是第一底 直接＋1
            if self.tableConfig[MFTDefine.CUR_BASE_COUNT] == 0:
                self.tableConfig[MFTDefine.CUR_BASE_COUNT] += 1
            ftlog.debug('MajiangTableLogic.beginGame, CUR_BASE_COUNT:', self.tableConfig[MFTDefine.CUR_BASE_COUNT])
	ftlog.debug('MajiangTableLogic ROUND_COUNT=',self.tableConfig[MFTDefine.ROUND_COUNT],' CUR_ROUND_COUNT=',self.tableConfig.get(MFTDefine.CUR_ROUND_COUNT, 0))
        for seatId in range(self.playerCount):
            self.player[seatId].play()
	    #if self.bankerMgr.remain_count >0:
            #    self.sendMsgTableInfo(seatId)
        self.tableTileMgr.setPlayers(self.player)    

        # 发牌之后修改牌桌状态
        self.__table_win_state = MTableState.TABLE_STATE_NEXT
        ftlog.info('MajiangTableLogic.beginGame tableWinState:', self.__table_win_state)
        if self.tableObserver:
            self.tableObserver.onGameEvent(MTableStatistic.TABLE_START
                    , self.player
                    , self.getTableConfig(MTDefine.TABLE_ROUND_ID, pktimestamp.getCurrentTimestamp()))

        return True
            
    def beginGame(self):
        """开始游戏
        """
        # 判断胡是否需要庄家id
        banker = self.queryBanker()
        if self.__win_rule_mgr.isNeedBankId():
            self.__win_rule_mgr.setBankerId(banker)
            
        # 判断是否连庄
        if self.bankerMgr.bankerRemainCount > 0:
            for player in self.player:
                util.sendPopTipMsg(player.userId, "恭喜玩家" + self.player[banker].name + "连庄")
	    if MPlayMode().isSubPlayMode(self.playMode, MPlayMode.QUESHOU):
                self.__table_config[MTDefine.WIN_BASE] = 1 + self.bankerMgr.bankerRemainCount
        else:
	    if MPlayMode().isSubPlayMode(self.playMode, MPlayMode.QUESHOU):
                self.__table_config[MTDefine.WIN_BASE] = 1
	for player in self.player:
 	    ftlog.debug('player state:',player.state)

        # 发牌
        self.shuffle()
	if MPlayMode().isSubPlayMode(self.playMode, MPlayMode.QUESHOU):
	    # 给庄家发一张牌，等待庄家出牌
            cp = self.player[self.__cur_seat]
            self.processAddTile(cp, MTableState.TABLE_STATE_NEXT)  

        #开局全体补花
        if self.checkTableState(MTableState.TABLE_STATE_BUFLOWER):
            flowers = self.flowerRuleMgr.getAllFlowers(self.player)
            flowerCount = self.flowerRuleMgr.getFlowerCount(flowers)
            self.flowerProcessor.setMsgProcessor(self.msgProcessor)
	    ftlog.debug('beginGame MTableState.TABLE_STATE_BUFLOWER',flowerCount,flowers)
            if flowerCount > 0:
		#time.sleep(2.0)
                self.flowerProcessor.initProcessor(MTableState.TABLE_STATE_BUFLOWER, flowers, True, self.curSeat)
            	self.msgProcessor.table_call_player_buFlower_start(self.getBroadCastUIDs())
		return

	#modify by youjun 05.02
	if (self.getTableConfig(MTDefine.CHANGE3TILES,0)):
            ftlog.debug('beginGame playMode:', self.playMode,' change3tiles config:',self.getTableConfig(MTDefine.CHANGE3TILES,0))
            self.change3tilesProcessor.reset()
            self.change3tilesSchedule()
	    self.change3tilesProcessor.onBankerAddedFirstTile()
            return True
        # 有定缺玩法的，设置进入定缺状态，庄家起手摸牌时不能打牌，且不显示胡牌
        if self.checkTableState(MTableState.TABLE_STATE_ABSENCE):
            self.absenceProcessor.reset()
            self.absenceSchedule()
            
        # 有定缺玩法的，开始让玩家做定缺选择
        if self.checkTableState(MTableState.TABLE_STATE_ABSENCE):
            self.absenceProcessor.onBankerAddedFirstTile()
	    return True	

        #开金
	if self.checkTableState(MTableState.TABLE_STATE_KAIJIN):
	    self.kaijinProcessor.initProcessor(MTableState.TABLE_STATE_KAIJIN
                        , self.bankerMgr.queryBanker()
                        , self.msgProcessor
                        , self.getBroadCastUIDs())
            return True        

        # 给庄家发一张牌，等待庄家出牌
        cp = self.player[self.__cur_seat]
        self.processAddTile(cp, MTableState.TABLE_STATE_NEXT) 
 
        return True

    def getRoundId(self):
        """获取局ID"""
        if self.runMode == MRunMode.CONSOLE:
            return pktimestamp.getCurrentTimestamp()
        else:
            from poker.entity.dao import daobase
            # 不影响table_logic的本地运行，这样引用
            return daobase.executeMixCmd('incrby', 'majiang2_round_id', 1)
        
    def checkLouHu(self, seatId):
        """判断当前座位号是否可以漏胡
        返回值：
        1）True 可以漏胡
        2）False 不可以漏胡
        """
        cp = self.players[seatId]
        if not cp.isTing():
            return False
        magicTiles = self.tableTileMgr.getMagicTiles(cp.isTing())
        ftlog.debug('MajiangTableLogic.checkLouHu seatId:', seatId
                    , ' magics:', magicTiles)
        
        #鸡西听后如果胡的是宝牌则直接胡(通宝／宝边 宝中宝／宝夹） 哈尔滨也追加此功能
        duiBaoConfig = self.tableConfig.get(MTDefine.DUI_BAO, 0)
        if duiBaoConfig:
            hzConfig = self.tableConfig.get(MTDefine.HONG_ZHONG_BAO, 0)
            isMagicAfterTingHu = self.__win_rule_mgr.isMagicAfertTingHu(cp.isTing()
                            , cp.winNodes
                            , magicTiles
                            , {"hongZhong": hzConfig})
            if isMagicAfterTingHu:
                # 扩展数据
                self.setCurSeat(seatId)
                ftlog.debug('self.setCurSeat 3',seatId)
		state = MTableState.TABLE_STATE_PASS_HU
                exInfo = MTableStateExtendInfo() 
                winInfo = {}
                magicTiles = self.tableTileMgr.getMagicTiles(True)
                tile = magicTiles[0]
                winInfo['tile'] = tile #直接把宝牌给过去
                winInfo['magicAfertTing'] = 1
                exInfo.appendInfo(state, winInfo)
                timeOut = self.__table_stater.getTimeOutByState(state)
                self.louHuProcesssor.initProcessor(self.actionID, cp.curSeatId, state, tile, exInfo, timeOut)
                return True

        # 第二种漏胡的情况，刮大风漏宝
        if self.tableConfig.get(MTDefine.GUA_DA_FENG, 0) and \
            cp.isTing() and \
            self.tableConfig.get(MTDefine.GUA_DA_FENG_CALC_MAGIC, 0) and \
            len(magicTiles) > 0:
            magicTile = magicTiles[0]
            mTiles = cp.copyTiles()
            # 加入手牌
            mTiles[MHand.TYPE_HAND].append(magicTile)
            quemen = -1
            if self.checkTableState(MTableState.TABLE_STATE_ABSENCE): 
	        quemen = self.absenceProcessor.absenceColor[cp.curSeatId]
            mGangs = self.gangRuleMgr.hasGang(mTiles, magicTile, MTableState.TABLE_STATE_NEXT,quemen)
            ftlog.debug('MajiangTableLogic.checkLouHu check GUA_DA_FENG_CALC_MAGIC tiles:', mTiles
                                , ' magicTile:', magicTile
                                , ' gangs:', mGangs)

            maddTileInGang = False
            for gang in mGangs:
                if magicTile not in gang['pattern']:
                    continue
                
                if cp.canGang(gang
                              , True
                              , mTiles
                              , magicTile
                              , self.winRuleMgr
                              , self.tableTileMgr.getMagicTiles(cp.isTing())
                              , {"louhu": 1}):
                    maddTileInGang = True
                    break

            if maddTileInGang:
                self.setCurSeat(seatId)
                ftlog.debug('self.setCurSeat 4',seatId)
		state = MTableState.TABLE_STATE_PASS_HU
                exInfo = MTableStateExtendInfo()
                winInfo = {}
                winInfo['tile'] = magicTile
                winInfo['daFeng'] = 1
                exInfo.appendInfo(state, winInfo)
                timeOut = self.__table_stater.getTimeOutByState(state)
                self.louHuProcesssor.initProcessor(self.actionID, cp.curSeatId, state, magicTile, exInfo, timeOut)
                return True
        
        return False
        
    def gameNext(self):
        """下一步，游戏的主循环
        """
        ftlog.debug( 'table.gameNext...' )
        changeMagicConfig = self.tableConfig.get(MTDefine.CHANGE_MAGIC, 0)
        canChangeMagic = True

        if changeMagicConfig and canChangeMagic:
            bChanged = False
            magics = self.tableTileMgr.getMagicTiles(True)
            while (len(magics) > 0) and (self.tableTileMgr.getVisibleTilesCount(magics[0]) == 3): 
                if not self.tableTileMgr.updateMagicTile():
                    break
                
                bChanged = True
                magics = self.tableTileMgr.getMagicTiles(True)

            if bChanged:
                # 发送换宝通知
                self.updateBao()
                # 换宝后，从自己开始判漏
                for nextIndex in range(0, self.playerCount):
                    seatId = (self.curSeat + nextIndex) % self.playerCount
                    if self.checkLouHu(seatId):
                        # 有人漏胡，处理漏胡 漏胡为自摸
                        self.setCurSeat(seatId)
                        ftlog.debug('self.setCurSeat 5',seatId)
			return

        if self.curState() == MTableState.TABLE_STATE_NEXT:
            self.__cur_seat = self.nextSeatId(self.__cur_seat)
            cp = self.player[self.__cur_seat]
            ftlog.debug('MajiangTableLogic.gameNext, canTingBeforeAddTile:',
                        self.tableConfig.get(MTDefine.TING_BEFORE_ADD_TILE, 0),
                        self.checkTableState(MTableState.TABLE_STATE_TING), cp.isTing())
            if self.checkTableState(MTableState.TABLE_STATE_TING) and \
                self.tableConfig.get(MTDefine.TING_BEFORE_ADD_TILE, 0) and \
                (not cp.isTing()):
                # 测试当前玩家是否可以听
                canTing, winNodes = self.tingRule.canTingBeforeAddTile(cp.copyTiles()
                                                   , self.tableTileMgr.tiles
                                                   , self.tableTileMgr.getMagicTiles(cp.isTing())
                                                   , self.__cur_seat
                                                   , cp.curSeatId
                                                   , self.actionID)
                ftlog.debug('MajiangTableLogic.gameNext, check ting before add tile, canTing:', canTing
                            , ' winNodes:', winNodes)
                if canTing:
                    self.tingBeforeAddCardProcessor.initProcessor(self.actionID, MTableState.TABLE_STATE_TING, cp.curSeatId, winNodes, 9)
                    winTiles = self.tingBeforeAddCardProcessor.getWinTiles()
                    tingResult = MTing.calcTingResult(winNodes[0]['winNodes'], self.tableTileMgr, cp.curSeatId)
                    ftlog.debug('MajiangTableLogic.gameNext tingBeforeAddCardProcessor winTiles:', winTiles)
                    self.msgProcessor.table_call_ask_ting(cp.curSeatId, self.actionID, winTiles, tingResult, 9)
                    return
                
            self.processAddTile(cp, MTableState.TABLE_STATE_NEXT)
            
    def nextSeatId(self, seatId):
        """计算下一个seatId
        """
        seatId = (seatId + 1) % self.__playerCount
        if self.checkTableState(MTableState.TABLE_STATE_XUEZHAN):
            if self.__players[seatId].state == MPlayer.PLAYER_STATE_WON:
                return self.nextSeatId(seatId)
            else:
                return seatId
        else:
            return seatId
        
    def preSeatId(self, seatId):
        """计算上家seatId
        """
        seatId = seatId - 1
        if seatId < 0:
            seatId += self.__playerCount
        return seatId
        
    def dropTile(self, seatId, dropTile, exInfo = {}):
        """玩家出牌"""
        ftlog.info( 'table.dropTile seatId:', seatId, ' dropTile:', dropTile)
        
        # 如果不是轮到此玩家出牌，不响应
        if self.curSeat != seatId:
            ftlog.debug( 'table.dropTile wrong seatId...',self.curSeat,seatId )
            return
        # 如果此玩家手里没有这张牌，不响应
        if not self.players[seatId].canDropTile(dropTile, self.playMode):
            return
	ftlog.debug('self.absenceProcessor.getState():', self.absenceProcessor.getState(),self.change3tilesProcessor.getState())
        # 换三张的时候不让出牌
	if self.change3tilesProcessor.getState() != 0:
	    return
	# 定缺的时候不让打牌
        if self.absenceProcessor.getState() != 0:
            return
	if MPlayMode().isSubPlayMode(self.playMode, MPlayMode.QUESHOU):
            if self.kaijinProcessor.getState()!= 0 and self.qiangjinProcessor.getState()!=0:
    	        return
	    else:
	        self.__qiangjin = False 
	ftlog.debug('self.kaijinProcessor.getState()=',self.kaijinProcessor.getState() ,' self.qiangjinProcessor.getState()=',self.qiangjinProcessor.getState())	

        # 花牌走补花处理
        if self.flowerRuleMgr.isFlower(dropTile):
            return self.buFlower(seatId, dropTile)

        # 天听状态不为0 不能出牌
        if self.tableConfig.get(MTDefine.TING_WITH_BEGIN, 0) and self.tianTingProcessor.getState() != 0:
            return False

        # 有玩家出牌，说明天听已过，不再需要听的状态
        if self.tableConfig.get(MTDefine.TING_WITH_BEGIN, 0) and self.checkTableState(MTableState.TABLE_STATE_TING):
            self.tableStater.clearState(MTableState.TABLE_STATE_TING)
            self.msgProcessor.setTianTing(False)

        # 当前玩家
        cp = self.players[seatId]
        canDrop, reason = cp.canDropTile(dropTile, self.playMode)
	ftlog.debug('MajiangTableLogic.dropTile canDrop:',canDrop,reason)
        if not canDrop:
            Util.sendShowInfoTodoTask(cp.userId, 9999, reason)
            return

        # 定缺功能中，如果玩家手上有对应的缺牌，就只能出那种牌
        '''
	if self.checkTableState(MTableState.TABLE_STATE_ABSENCE):
            absenceColor = self.absenceProcessor.absenceColor[seatId]
            tileArr = MTile.changeTilesToValueArr(cp.handTiles)
            if MTile.getTileCountByColor(tileArr, absenceColor) > 0 and MTile.getColor(dropTile) != absenceColor:
                return
	'''
	if MPlayMode().isSubPlayMode(self.playMode, MPlayMode.QUESHOU):
            if dropTile in cp.limitTiles and self.playMode == 'queshou-lianjiang2':
                return

	if self.checkTableState(MTableState.TABLE_STATE_XUELIU):
	    if cp.isWon() and cp.curTile != dropTile:
		ftlog.debug('MajiangTableLogic.dropTile cp.isWon:',cp.isWon(),' cp.curTile:',cp.curTile,' dropTile:',dropTile)
		return
        cp.actionDrop(dropTile)

        # 重置玩家的过碰状态，和连杠次数
        cp.resetGuoPengTiles()
        cp.recordAndResetLianGangNum()

        # 设置出牌信息
        self.tableTileMgr.setDropTileInfo(dropTile, seatId)
        dropSeat = self.curSeat
        #判断dropHu,必须在上一步设置出牌信息之后,因为取的是上一步dropTile加到已出牌组里后的数据
        winResultDrop, _ = self.winRuleMgr.isDropHu(cp)
        if winResultDrop:
            self.addCardProcessor.reset()
            self.dropCardProcessor.reset()
            self.qiangGangHuProcessor.reset()
            self.qiangExmaoPengProcessor.reset()
            # 修改操作标记
            self.incrActionId('dropWin')
            # 向玩家发送出牌结果，其他人收的到出牌结果么？
            for seat in range(self.__playerCount):
                newSeat = (seatId + seat) % self.playerCount
                # 向玩家发送出牌结果
                message = self.msgProcessor.table_call_drop(dropSeat, self.player[newSeat], dropTile, 0, {}, self.actionID, 0)
                self.msgProcessor.send_message(message, [self.player[ newSeat].userId])
            # 庄家出牌和
            self.gameWin(seatId, dropTile)
            return
             
        # 设置出牌
        self.addCardProcessor.reset()
        self.dropCardProcessor.reset()
        self.qiangGangHuProcessor.reset()
        self.qiangExmaoPengProcessor.reset()
        self.dropCardProcessor.initTile(dropTile, self.curSeat)
        
        # 修改操作标记
        self.incrActionId('dropTile')
                
        # 测试其他玩家对于这张牌的处理
        dropMessages = [None for _ in range(self.playerCount)]
        for seat in range(0, self.playerCount):
            newSeat = (seatId + seat) % self.playerCount
            if newSeat == dropSeat:
                winTiles = None
                if self.tableConfig.get(MFTDefine.CALC_WIN_TILES_AT_DROP, 0):
                    winTiles = self.winRuleMgr.calcWinTiles(cp.copyTiles())
                message = self.msgProcessor.table_call_drop(dropSeat, cp, dropTile, 0, {}, self.actionID, 0, winTiles)
                dropMessages[dropSeat] = message
            else:
                _, message = self.processDropTile(dropSeat, self.player[newSeat], dropTile)
                dropMessages[newSeat] = message
	

        # 如果大家都对这张出牌没有反应，加入门前牌堆
        if self.dropCardProcessor.getState() == 0:
            ftlog.debug('dropTile, no user wants tile:', dropTile, ' put to men tiles. seatId:', seatId)
            self.tableTileMgr.setMenTileInfo(dropTile, seatId)
            
        # 最后一起给大家发送消息
        for index in range(self.playerCount):
            self.msgProcessor.send_message(dropMessages[index], [self.player[index].userId])
            
        #听牌之后的漏胡牌情况处理
        if self.checkLouHu(seatId):
            # 消息发送完了，清空其他所有人的操作信息，除了胡牌
            for newSeatId in range(self.playerCount):
                if newSeatId == seatId:
                    continue
                self.dropCardProcessor.resetSeatIdExceptWin(newSeatId)
                
    def processDropTile(self, dropSeat, cp, tile):
        ftlog.debug( 'MajiangTable.processDropTile...tile:',tile )
       	#modify by youjun 04.26 
        nowSeat = self.curSeat
        # 如果该玩家已经是胡的状态,不进行下面的处理
  	if self.checkTableState(MTableState.TABLE_STATE_XUEZHAN):
            if cp.state == MPlayer.PLAYER_STATE_WON:
                message = self.msgProcessor.table_call_drop(nowSeat, cp, tile, 0, {}, self.actionID, 0)
                return cp.state, message
	#modify end
        # 取出手牌
        tiles = cp.copyTiles()
        tiles[MHand.TYPE_HAND].append(tile)
        oriTiles = cp.copyTiles()
        oriTiles[MHand.TYPE_HAND].append(tile)
        
        nextSeatId = self.nextSeatId(self.curSeat)
        state = 0
        laiziPiNoPeng=0
        exInfo = MTableStateExtendInfo()

        if (not self.tableTileMgr.isHaidilao()): #海底牌不能吃、碰、杠、点炮，只能自摸
            # 听牌了不可以吃
            chiResults = []
            if (not cp.isTing()) and (not cp.isWon()) and self.checkTableState(MTableState.TABLE_STATE_CHI):
                # 检测是否可吃
                chiResults = self.chiRuleMgr.hasChi(tiles, tile)
                if len(chiResults) != 0 and \
                    self.winRuleMgr.canWinAfterChiPengGang(tiles):
                    if nextSeatId == cp.curSeatId:
                        state |= MTableState.TABLE_STATE_CHI
                        ftlog.debug('MajiangTable.processDropTile seatId:', cp.curSeatId, ' can chi:', chiResults)
                        exInfo.setInfo(MTableState.TABLE_STATE_CHI, chiResults)
                    
                    # 判断吃牌里面的吃听
                    if self.checkTableState(MTableState.TABLE_STATE_GRABTING):
                        for chiResult in chiResults:
                            for _tile in chiResult:
                                tiles[MHand.TYPE_HAND].remove(_tile)
                            tiles[MHand.TYPE_CHI].append(chiResult)
                            
                            # 判断吃听 吃之后加听
                            tingResult, tingArr = self.tingRule.canTing(tiles, self.tableTileMgr.tiles, tile, self.tableTileMgr.getMagicTiles(cp.isTing()), \
                                                                               self.curSeat, cp.curSeatId, self.actionID)
                            if tingResult:
                                state |= MTableState.TABLE_STATE_GRABTING
                                chiTing = {}
                                chiTing['tile'] = tile
                                chiTing['pattern'] = chiResult
                                chiTing['ting'] = tingArr
                                exInfo.appendInfo(MTableState.TABLE_STATE_CHI | MTableState.TABLE_STATE_GRABTING, chiTing)
                                ftlog.debug( 'MajiangTable.processDropTile seatId:', cp.curSeatId, ' can ting with chi patter:', chiResult )
                            # 还原手牌    
                            tiles[MHand.TYPE_CHI].pop(-1)
                            tiles[MHand.TYPE_HAND].extend(chiResult)
            
            # 碰
            if (not cp.isTing()) and (not cp.isWon()) and self.checkTableState(MTableState.TABLE_STATE_PENG) and not laiziPiNoPeng \
                    and self.maoRuleMgr.checkPengMao(tile, self.tableConfig.get(MTDefine.MAO_DAN_SETTING, MTDefine.MAO_DAN_NO),
                                         tiles[MHand.TYPE_MAO]):
                pengSolutions = self.pengRuleMgr.hasPeng(tiles, tile, cp.curSeatId)
                canDrop, _ = cp.canDropTile(tile, self.playMode)
                if not canDrop:
                    pengSolutions = []
                #modify by youjun 04.28
                if self.checkTableState(MTableState.TABLE_STATE_ABSENCE):
                    # 定缺牌不可碰
                    def pengSolutionsFilter(pengSolutions):
                        quemen = self.absenceProcessor.absenceColor[cp.curSeatId]
			ftlog.debug('pengSolutionFilter quemen :',quemen)
                        magics = self.tableTileMgr.getMagicTiles(cp.isTing())
                        for tile in pengSolutions:
                            if tile != 0 and tile not in magics:
                                if MTile.getColor(tile) == quemen:
                                    return False
                        return True

                    pengSolutions = filter(pengSolutionsFilter, pengSolutions)

                ftlog.debug('MajiangTable.processDropTile hasPeng pengSolution:', pengSolutions)
                if len(pengSolutions) > 0 and self.winRuleMgr.canWinAfterChiPengGang(tiles):
                    # 可以碰，给用户碰的选择
                    state = state | MTableState.TABLE_STATE_PENG
                    ftlog.debug( 'MajiangTable.processDropTile seatId:', cp.curSeatId, ' can peng' )
                    exInfo.setInfo(MTableState.TABLE_STATE_PENG, pengSolutions)
                    
                    for pengSolution in pengSolutions:
                        ftlog.debug('MajiangTable.processDropTile check pengSolution:', pengSolution, ' canTingOrNot')
                        if self.checkTableState(MTableState.TABLE_STATE_GRABTING):
                            for _tile in pengSolution:
                                tiles[MHand.TYPE_HAND].remove(_tile)
                            tiles[MHand.TYPE_PENG].append(pengSolution)
                            
                            # 判断碰听，碰加听
                            tingResult, tingArr = self.tingRule.canTing(tiles, self.tableTileMgr.tiles, tile, self.tableTileMgr.getMagicTiles(cp.isTing()), \
                                                                               self.curSeat, cp.curSeatId, self.actionID)
                            if tingResult:
                                state |= MTableState.TABLE_STATE_GRABTING
                                ftlog.debug( 'MajiangTable.processDropTile seatId:', cp.curSeatId, ' can ting with peng' )
                                pengTing = {}
                                pengTing['tile'] = tile
                                pengTing['ting'] = tingArr
                                pengTing['pattern'] = pengSolution
                                exInfo.appendInfo(MTableState.TABLE_STATE_PENG | MTableState.TABLE_STATE_GRABTING, pengTing)
                            # 还原手牌    
                            tiles[MHand.TYPE_PENG].pop(-1)
                            tiles[MHand.TYPE_HAND].extend(pengSolution)

            # 粘
            if (not cp.isTing()) and self.checkTableState(MTableState.TABLE_STATE_ZHAN):
                # 判断粘听，粘加听
                #粘必须手里有这张牌
                ftlog.debug('MajiangTable.processDropTile try zhan, tile:', tile
                            , ' handTiles:', oriTiles[MHand.TYPE_HAND])
                
                tempcount = MTile.getTileCount(tile,oriTiles[MHand.TYPE_HAND])
                if tempcount ==2 or tempcount ==4:
                    tingResult, tingArr = self.tingRule.canTing(oriTiles, self.tableTileMgr.tiles, tile, self.tableTileMgr.getMagicTiles(cp.isTing()))
                    ftlog.debug('MajiangTable.processDropTile try zhan result tingResult:', tingResult
                                , ' tingArr:', tingArr)
                    
                    if tingResult and len(tingArr) > 0:
                        newTingArr = []
                        for tingSolutin in tingArr:
                            newTingSolution = {}
                            winNodes = tingSolutin['winNodes']
                            newWinNodes = []
                            for winNode in winNodes:
                                pattern = winNode['pattern']
                                if len(pattern) == 7:
                                    newWinNodes.append(winNode)
                            if len(newWinNodes) > 0:
                                newTingSolution['dropTile'] = tingSolutin['dropTile']
                                newTingSolution['winNodes'] = newWinNodes
                                newTingArr.append(newTingSolution)
                        ftlog.debug('MajiangTable.processDropTile try zhan adjust result:', newTingArr)
                            
                        if len(newTingArr) > 0:
                            #ting QiDui
                            zhanSolution = [tile,tile]
                            ftlog.debug('MajiangTable.processDropTile hasPeng zhanSolution:', zhanSolution)
                            state |= MTableState.TABLE_STATE_ZHAN
                            state |= MTableState.TABLE_STATE_GRABTING
                            ftlog.debug( 'MajiangTable.processDropTile seatId:', cp.curSeatId, ' can ting with zhan' )
                            zhanTing = {}
                            zhanTing['tile'] = tile
                            zhanTing['ting'] = newTingArr
                            zhanTing['pattern'] = zhanSolution
                            exInfo.appendInfo(MTableState.TABLE_STATE_ZHAN | MTableState.TABLE_STATE_GRABTING, zhanTing) 
                            tiles[MHand.TYPE_HAND].remove(tile)
                            tiles[MHand.TYPE_HAND].extend(zhanSolution)
            
            # 杠，出牌时，只判断手牌能否组成杠
            canGang = True
	    if self.playMode == 'luosihu-luosihu' and cp.isTing():
		if not self.tableConfig.get(MTDefine.GANGWITHTING):
		    canGang = False
            if canGang and self.checkTableState(MTableState.TABLE_STATE_GANG) and (not (state & MTableState.TABLE_STATE_ZHAN)):
		quemen = -1
		if self.checkTableState(MTableState.TABLE_STATE_ABSENCE): 
	            quemen = self.absenceProcessor.absenceColor[cp.curSeatId]
                gangs = self.gangRuleMgr.hasGang(tiles, tile, MTableState.TABLE_STATE_DROP,quemen)
                newGangs = []
                for gang in gangs:
                    checkTile = gang['pattern'][0]
                    canDrop, _ = cp.canDropTile(checkTile, self.playMode)
                    if canDrop:
                        newGangs.append(gang)
                gangs = newGangs
		ftlog.debug('MajiangTable.processDropTile gangs=',gangs)
                if len(gangs) > 0 and self.winRuleMgr.canWinAfterChiPengGang(tiles):
                    for gang in gangs:
                        if gang['style'] != MPlayerTileGang.MING_GANG and gang['style'] !=MPlayerTileGang.CHAOTIANXIAO_MING:
                            continue
                        # 可以杠，给用户杠的选择，听牌后，要滤掉影响听口的杠
                        if cp.canGang(gang, True, tiles, tile, self.winRuleMgr, self.tableTileMgr.getMagicTiles(cp.isTing())):
                            state = state | MTableState.TABLE_STATE_GANG
                            ftlog.debug('MajiangTable.processDropTile seatId:', cp.curSeatId, ' can gang: ', gang)
                            exInfo.appendInfo(MTableState.TABLE_STATE_GANG, gang)
                            if self.checkTableState(MTableState.TABLE_STATE_FANPIGU):
                                pigus = self.tableTileMgr.getPigus()
                                exInfo.appendInfo(MTableState.TABLE_STATE_FANPIGU, pigus)
    
                        # 如果杠完，上任何一张牌，都可以听，则可以有杠听。此时确定不了听牌的听口，需杠牌上牌后确定听口
                        if (not cp.isTing()) and self.checkTableState(MTableState.TABLE_STATE_GRABTING):
                            ftlog.debug('handTile:', tiles[MHand.TYPE_HAND])
                            for _tile in gang['pattern']:
                                tiles[MHand.TYPE_HAND].remove(_tile)
                            tiles[MHand.TYPE_GANG].append(gang)
                            
                            leftTiles = copy.deepcopy(self.tableTileMgr.tiles)
                            newTile = leftTiles.pop(0)
                            tiles[MHand.TYPE_HAND].append(newTile)
                            
                            # 判断杠听，杠加听
                            tingResult, tingArr = self.tingRule.canTing(tiles, leftTiles, tile, self.tableTileMgr.getMagicTiles(cp.isTing()), \
                                                                               self.curSeat, cp.curSeatId, self.actionID)
                            if tingResult:
                                state |= MTableState.TABLE_STATE_GRABTING
                                ftlog.debug( 'MajiangTable.processDropTile seatId:', cp.curSeatId, ' can ting with gang' )
                                gangTing = {}
                                gangTing['tile'] = tile
                                gangTing['ting'] = tingArr
                                gangTing['pattern'] = gang['pattern']
                                gangTing['style'] = gang['style']
                                exInfo.appendInfo(MTableState.TABLE_STATE_GANG | MTableState.TABLE_STATE_TING, gangTing)
                                
                            #还原手牌
                            tiles[MHand.TYPE_GANG].pop(-1)
                            tiles[MHand.TYPE_HAND].extend(gang['pattern'])
                            tiles[MHand.TYPE_HAND].remove(newTile)

        winResult = False
        needZimo = False
	winMode = 0
        if self.checkTableState(MTableState.TABLE_STATE_TING) \
            and self.tableConfig.get(MTDefine.ZIMO_AFTER_TING, 0) == 1 \
            and cp.isTing():
            needZimo = True
            
        if self.tableConfig.get(MTDefine.WIN_BY_ZIMO, MTDefine.WIN_BY_ZIMO_NO) == MTDefine.WIN_BY_ZIMO_OK:
            needZimo = True
	ftlog.debug('neewZimo',self.tableConfig.get(MTDefine.WIN_BY_ZIMO, MTDefine.WIN_BY_ZIMO_NO),'  MTDefine.WIN_BY_ZIMO_NO:',MTDefine.WIN_BY_ZIMO_OK,'  needZimo',needZimo)
        # 牌池数少于某个设置时，不和点炮
        if (not self.tableTileMgr.isHaidilao()) and (not needZimo):
            magics = self.tableTileMgr.getMagicTiles(cp.isTing())
            if self.tableConfig.get(MTDefine.HONG_ZHONG_BAO, 0) and MTile.TILE_HONG_ZHONG not in magics:
                magics.append(MTile.TILE_HONG_ZHONG)
                
            # 给winMgr传入当前杠牌的座位号
            self.winRuleMgr.setLastGangSeat(self.latestGangState)
            self.winRuleMgr.setCurSeatId(self.curSeat)
	    #modify by youjun 04.28
	    if self.checkTableState(MTableState.TABLE_STATE_ABSENCE):
                absenceColor = self.absenceProcessor.absenceColor[cp.curSeatId]
                tileArr = MTile.changeTilesToValueArr(cp.handTiles)
                if MTile.getTileCountByColor(tileArr, absenceColor) > 0:
                    winResult = False
                else:
                    winResult, winPattern,_ = self.winRuleMgr.isHu(tiles, tile, cp.isTing(), MWinRule.WIN_BY_OTHERS, self.tableTileMgr.getMagicTiles(cp.isTing()), cp.winNodes, \
                                                         self.curSeat, cp.curSeatId, self.actionID, False)
		    ftlog.debug( 'MajiangTable.processDropTile, winResutl:', winResult, 'tile',tile, 'winPattern:', winPattern ) 
		    self.winRuleMgr.setCurSeatId(-1)
            else:
                winResult, winPattern,winMode = self.winRuleMgr.isHu(tiles, tile, cp.isTing(), MWinRule.WIN_BY_OTHERS, self.tableTileMgr.getMagicTiles(cp.isTing()), cp.winNodes, \
                                                     self.curSeat, cp.curSeatId, self.actionID, False)
                ftlog.debug( 'MajiangTable.processDropTile, winResutl:', winResult, 'tile',tile, 'winPattern:', winPattern )     
		self.winRuleMgr.setCurSeatId(-1)
	if MPlayMode().isSubPlayMode(self.playMode, MPlayMode.QUESHOU):
	    cp.setWinMode(winMode)
	
        if self.checkTableState(MTableState.TABLE_STATE_HU) and winResult:
            # 可以和，给用户和的选择
            state = state | MTableState.TABLE_STATE_HU
            winInfo = {}
   	    if MPlayMode().isSubPlayMode(self.playMode, MPlayMode.QUESHOU):
                winInfo['winMode'] = winMode
                exInfo.appendInfo(MTableState.TABLE_STATE_HU, winInfo)
            if self.tableConfig.get(MTDefine.WIN_AUTOMATICALLY, 0):
                state = MTableState.TABLE_STATE_HU
            ftlog.debug( 'MajiangTable.processDropTile seatId:', cp.curSeatId, ' can win stats:',state)
            if self.winRuleMgr.canDirectHuAfterTing() and cp.isTing():
                timeOut = self.tableStater.getTimeOutByState(state)
                self.dropCardProcessor.initProcessor(self.actionID, cp.curSeatId, state, exInfo, timeOut)
                self.gameWin(cp.curSeatId, tile)

        timeOut = self.tableStater.getTimeOutByState(state)
        self.dropCardProcessor.initProcessor(self.actionID, cp.curSeatId, state, exInfo, timeOut)
        message = self.msgProcessor.table_call_drop(dropSeat, cp, tile, state, exInfo, self.actionID, timeOut)
        # 返回结果
        return state, message
    
    def getBaoPaiInfo(self):
        """获取宝牌的协议信息"""
        bNodes = []
        magics = self.tableTileMgr.getMagicTiles(True)
        for magic in magics:
            bNode = {}
            bNode['tile'] = magic
            bNodes.append(bNode)
            
        abandones = self.tableTileMgr.getAbandonedMagics()
        aNodes = []
        for ab in abandones:
            aNode = {}
            aNode['tile'] = ab
            aNodes.append(aNode)
        
        ftlog.debug('MajiangTable.getBaoPaiInfo baopaiInfo:', bNodes, ' abandonesInfo:', aNodes)
        return bNodes, aNodes
    
    def updateBao(self):
        """通知已听牌玩家宝牌"""
        bNodes, aNodes = self.getBaoPaiInfo()
        ftlog.debug('MajiangTable.updateBao bNodes:', bNodes, ' aNodes:', aNodes)
        if len(bNodes) == 0 and len(aNodes) == 0:
            return
        
        #鸡西设置了暗宝 不通知客户端
        if  self.tableConfig.get(MTDefine.MAGIC_HIDE, 1):
            bNodes = None
            
        for player in self.player:
            self.msgProcessor.table_call_baopai(player, None, aNodes)
                
    def tingBeforeAddCard(self, seatId, actionId):
        if self.tingBeforeAddCardProcessor.updateProcessor(actionId, MTableState.TABLE_STATE_TING, seatId):
            winNodes = self.tingBeforeAddCardProcessor.winNodes
            ftlog.debug('MajiangTable.tingBeforeAddCard seatId:', seatId
                        , ' actionId:', actionId
                        , ' winNodes:', winNodes)
            self.player[seatId].actionTing(winNodes[0]['winNodes'])
            self.tableTileMgr.appendTingIndex(seatId)
            tingResult = MTing.calcTingResult(winNodes[0]['winNodes'], self.tableTileMgr, seatId)
            self.player[seatId].setTingResult(tingResult)
            
	    self.setCurSeat(seatId)
    	    ftlog.debug('self.setCurSeat 6',seatId)
            # actionTingLiang当中会根据听亮模式，来决定是否亮牌，默认不亮牌
            self.player[seatId].actionTingLiang(self.tableTileMgr, -1, self.actionID, [])
    
            allWinTiles = []
            for player in self.player:
                if player.tingLiangWinTiles:
                    allWinTiles.append(player.tingLiangWinTiles)
                else:
                    allWinTiles.append(None)
                    
            self.incrActionId('tingBeforeAddCard')
            # 重置状态机
            self.tingBeforeAddCardProcessor.reset()
            for player in self.player:
                # 把听牌信息发送给所有玩家，给自己主要是标示自己要胡的牌
                self.msgProcessor.table_call_after_ting(self.player[self.curSeat]
                    , self.actionID
                    , player.userId
                    , allWinTiles
                    , tingResult)
            # 发牌
            self.processAddTile(self.player[seatId], MTableState.TABLE_STATE_NEXT)
    
    def tingAfterDropCard(self, seatId, dropTile, kouTiles, exInfo):
        """听牌状态"""
        winNodes  = exInfo.getWinNodesByDropTile(dropTile)
        ftlog.info('MajiangTable.tingAfterDropCard, winNodes:', winNodes,' dropTile:',dropTile)
	magicTile=self.tableTileMgr.getMagicTile()	

        jinkanDrop = None
	if MPlayMode().isSubPlayMode(self.playMode,MPlayMode.QUESHOU) and magicTile:
            for winNode in winNodes:
                patterns = winNode['pattern']
                for pattern in patterns:
		    if jinkanDrop:
		        break
                    if len(pattern) == 3:
                        if (pattern[0] == magicTile - 1) and (pattern[2] == magicTile + 1):
			    jinkanDrop = pattern
                        if magicTile % 10 == 3:
                           if (pattern[0] == magicTile - 2) and (pattern[1] == magicTile - 1):
			        jinkanDrop = pattern
                        if magicTile % 10 == 7:
                            if (pattern[2] == magicTile + 2) and (pattern[1] == magicTile + 1):    
    			        jinkanDrop = pattern
	    if jinkanDrop:
		self.players[seatId].setJinkanDrop(jinkanDrop)

        self.players[seatId].actionTing(winNodes)
	tingResult = MTing.calcTingResult(winNodes, self.tableTileMgr, seatId)
        self.players[seatId].setTingResult(tingResult)
        
        self.tableTileMgr.appendTingIndex(seatId)
        self.setCurSeat(seatId)
	ftlog.debug('self.setCurSeat 7',seatId)        
        # actionTingLiang当中会根据听亮模式，来决定是否亮牌，默认不亮牌
        self.players[seatId].actionTingLiang(self.tableTileMgr, dropTile, self.actionID, kouTiles)

        allWinTiles = []
        for player in self.players:
            if player.tingLiangWinTiles:
                allWinTiles.append(player.tingLiangWinTiles)
            else:
                allWinTiles.append(None)

        # 重置状态机
        self.addCardProcessor.reset() 
        self.dropCardProcessor.reset()
        self.qiangGangHuProcessor.reset()
        self.qiangExmaoPengProcessor.reset()
        
        for player in self.players:
            # 把听牌信息发送给所有玩家，给自己主要是标示自己要胡的牌
            self.msgProcessor.table_call_after_ting(self.players[seatId]
                , self.actionID
                , player.userId
                , allWinTiles
                , tingResult
		,jinkanDrop)
	
	if self.isSeenTiles():
            self.msgProcessor.table_call_seen_tiles_broadcast(self.getBroadCastUIDs())
        # 出牌
        self.dropTile(seatId, dropTile, {"updateBao": True})

    def isSeenTiles(self):
        if self.playMode != 'luosihu-luosihu':
            return False
        tingCount = 0
        for player in self.players:
            if player.isTing() or player.isWon():
                tingCount = tingCount + 1
        if tingCount == self.playerCount:
            return True
        return False 

    def tianTing(self, seatId, actionId):
        if self.tianTingProcessor.updateProcessor(seatId):
            # 如果是庄家发过的 不广播所有人
            if self.queryBanker() != seatId:
                winNodes = self.tianTingProcessor.winNodes[seatId]
                ftlog.debug('MajiangTable.tianTing seatId:', seatId
                            , ' winNodes:', winNodes)
                self.player[seatId].actionTing(winNodes[0]['winNodes'])
                tingResult = MTing.calcTingResult(winNodes[0]['winNodes'], self.tableTileMgr, seatId)
                self.player[seatId].setTingResult(tingResult)
                self.tableTileMgr.appendTingIndex(seatId)

                for player in self.player:
                    # 把听牌信息发送给所有玩家，给自己主要是标示自己要胡的牌
                    self.msgProcessor.table_call_after_ting(self.players[seatId]
                                                        , self.actionID
                                                        , player.userId
                                                        , winNodes
                                                        , tingResult)

        if self.tianTingProcessor.getState() == 0:
            #self.msgProcessor.setTianTing(False)
            for player in self.player:
                if player.curSeatId == self.queryBanker():
                    self.msgProcessor.table_call_tian_ting_over(player.curSeatId, self.actionID)

    """
    以下四种情况为别人打出的牌，其他人可以有的行为
    分别是
        吃
        碰
        杠
        胡
    同一人或者多个人有不同的选择，状态机的大小代表优先级。
    响应的规则是：
    优先响应最高优先级的操作，最高优先级的操作取消，响应次高优先级的操作。
    一人放弃响应，此人的状态机重置
    
    特殊说明：
        此时当前座位还是出牌的人
        获取出牌之外的人的状态进行比较
    """  
    def chiTile(self, seatId, chiTile, chiPattern, state = MTableState.TABLE_STATE_CHI):
        """吃别人的牌
        只有一个人，且只判断__drop_card_processor
        """
        ftlog.info('MajiangTable.chiTile chiTile:', chiTile
                   , ' chiPattern:', chiPattern
                   , ' seatId:', seatId)
        if not chiTile in chiPattern:
            chiTile = self.players[self.curSeat].lastDropTile 
        #调整pattern顺序
        adjustPattern = copy.deepcopy(chiPattern)
        if len(adjustPattern) == 3:
            adjustPattern.remove(chiTile)
            chiPattern = [adjustPattern[0], chiTile, adjustPattern[1]]
            ftlog.info('MajiangTable.chiTile adjust chiTile:', chiTile, 'chiPattern:', chiPattern)
        
        cp = self.__players[seatId]
        # 只传吃牌的组合，如果在听牌吃牌中，自动听牌，暂时做的是这样
        if self.__drop_card_processor.updateProcessor(self.actionID, seatId, state, chiTile, chiPattern):
            exInfo = self.__drop_card_processor.getExtendResultBySeatId(seatId)
            self.__drop_card_processor.reset()
            lastSeatId = self.curSeat
            cp.actionAdd(chiTile)
            cp.actionChi(chiPattern, chiTile, self.actionID, lastSeatId)
            self.__cur_seat = cp.curSeatId
            self.incrActionId('chiTile')
            
            chiTingNotGrab = False
            if self.checkTableState(MTableState.TABLE_STATE_TING) and self.__ting_rule_mgr.canTingAfterPeng(cp.copyTiles()):
                _, tingArr = self.__ting_rule_mgr.canTing(cp.copyTiles()
                                                          , self.tableTileMgr.tiles
                                                          , chiTile
                                                          , self.tableTileMgr.getMagicTiles(cp.isTing())
                                                          , self.__cur_seat, cp.curSeatId
                                                          , self.actionID)
                if len(tingArr) > 0:
                    exInfo.appendInfo(MTableState.TABLE_STATE_TING, tingArr)
                    chiTingNotGrab = True
                    ftlog.debug( 'MajiangTable.chiTile seatId:', cp.curSeatId, ' can ting with chi (not grab ting)' )
                    
            timeOut = self.__table_stater.getTimeOutByState(state)
            # 吃牌转出牌，抢听变为听
            if state & MTableState.TABLE_STATE_GRABTING or chiTingNotGrab:
                self.addCardProcessor.initProcessor(self.actionID, MTableState.TABLE_STATE_TING, cp.curSeatId, chiTile, exInfo, timeOut)
                self.addCardProcessor.setMustTing(state & MTableState.TABLE_STATE_GRABTING)
            else:
                self.addCardProcessor.initProcessor(self.actionID, MTableState.TABLE_STATE_DROP, cp.curSeatId, chiTile, exInfo, timeOut)
                
            ftlog.debug('chiTile init addCardProcessor state:', state
                    , ' chiTile:', chiTile
                    , ' exInfo.extend:', exInfo.extend)
            
            actionInfo = {}
            if state & MTableState.TABLE_STATE_GRABTING:
                # {'tile': 28, 'pattern': [27, 28, 29], 'ting': [{'winNodes': [{'winTile': 24, 'pattern': [[28, 28], [23,       24, 25], [6, 7, 8]], 'winTileCount': 2}], 'dropTile': 15}]}
                ting_action = None
                ftlog.debug('chiTile grabTing exInfo.extend:', exInfo.extend)
                tingInfo = exInfo.extend['chiTing'][0]
                ftlog.debug('chiTile grabTing tingInfo:', tingInfo)
                # [8,[[12,1,1]]]
                ting_action = exInfo.getGrabTingAction(tingInfo, seatId, self.tableTileMgr, True)
                ftlog.debug('chiTile after chi, ting_action:', ting_action)
                actionInfo['ting_action'] = ting_action
                
            # 非抢听情况下，部分玩法如果能碰后听牌，需要马上听牌
            if chiTingNotGrab:
                ting_action_not_grab = exInfo.getTingResult(self.tableTileMgr, seatId)
                if ting_action_not_grab:
                    tingliang_action = exInfo.getTingLiangResult(self.tableTileMgr)
                    if tingliang_action:
                        actionInfo['tingliang_action'] = tingliang_action
                    kou_ting_action = exInfo.getCanKouTingResult(self.tableTileMgr, seatId)
                    if kou_ting_action:
                        actionInfo['kou_ting_action'] = kou_ting_action
                    #抢听把ting_action占用了，只能用ting_action_not_grab区分
                    actionInfo['ting_action_not_grab'] = ting_action_not_grab
                    
            ftlog.debug("chiTileAfterActionInfo", actionInfo)

            # 判断锚/蛋牌
            if self.checkTableState(MTableState.TABLE_STATE_FANGMAO):
                maoInfo = {}
                if self.ifCalcFangDan(cp.curSeatId) and (not cp.isTing()):
                    isFirstAddtile = self.isFirstAddTile(cp.curSeatId)
                    maos = self.maoRuleMgr.hasMao(cp.copyHandTiles()
                                       , self.tableConfig.get(MTDefine.MAO_DAN_SETTING, MTDefine.MAO_DAN_NO)
                                       , cp.getMaoTypes(), isFirstAddtile
									   , {"maoType":cp.getPengMaoTypes()})
                    if len(maos) > 0:
                        maoInfo['mao_tiles'] = maos

                if not cp.isTing():
                    extendMaos = self.maoRuleMgr.hasExtendMao(cp.copyHandTiles(), cp.getMaoTypes())
                    if len(extendMaos) > 0:
                        maoInfo['mao_extends'] = extendMaos

                if ('mao_tiles' in maoInfo) or ('mao_extends' in maoInfo):
                    exInfo.appendInfo(MTableState.TABLE_STATE_FANGMAO, maoInfo)

            # 判断补花
            if self.checkTableState(MTableState.TABLE_STATE_BUFLOWER):
                cp = self.player[seatId]
                flowers = self.flowerRuleMgr.hasFlower(cp.copyHandTiles())#手中剩余花牌
                if len(flowers) > 0:
                    if flowers[0] and self.flowerRuleMgr.isFlower(flowers[0]):
                        # 执行补花
                        cp.handTiles.remove(flowers[0])
                        cp.flowers.append(flowers[0])
                        self.tableTileMgr.setFlowerTileInfo(flowers[0], seatId)

                        # 累计花分
                        cp.addFlowerScores(1)
                        self.tableTileMgr.addFlowerScores(1, seatId)
                        self.msgProcessor.table_call_bu_flower_broadcast(seatId, flowers[0], cp.flowers,
                                                                         self.tableTileMgr.flowerScores(seatId),
                                                                         self.getBroadCastUIDs())
                        self.processAddTileSimple(cp)




            # 吃完出牌，广播吃牌，如果吃听，通知用户出牌听牌
            for player in self.player:
                self.__msg_processor.table_call_after_chi(lastSeatId
                        , self.curSeat
                        , chiTile
                        , chiPattern
                        , timeOut
                        , self.actionID
                        , player
                        , actionInfo
                        , exInfo)
                
        self.changeMagicTileAfterChiPengExmao()
            
    def pengTile(self, seatId, tile, pengPattern, state):
        """碰别人的牌
        只有一个人，有可能是碰别人打出的牌，也有可能是抢锚碰
        """
        cp = self.__players[seatId]
        exInfo = None
        checkPassDropPro = self.__drop_card_processor.updateProcessor(self.actionID, seatId, state, tile, pengPattern)
        ftlog.debug('MajiangTableLogic.pengTile, checkPassDropPro', checkPassDropPro)
        checkPassQiangExmaoPro = False
        if checkPassDropPro:
            exInfo = self.dropCardProcessor.getExtendResultBySeatId(seatId)
            self.dropCardProcessor.reset()
        else: 
            checkPassQiangExmaoPro = self.qiangExmaoPengProcessor.updateProcessor(self.actionID, seatId, MTableState.TABLE_STATE_PENG, tile, pengPattern)
            ftlog.debug('MajiangTableLogic.pengTile, checkPassQiangExmaoPro', checkPassQiangExmaoPro)
            if checkPassQiangExmaoPro:
                exInfo = self.qiangExmaoPengProcessor.exmaoExtend
                cpExmao = self.player[self.qiangExmaoPengProcessor.curSeatId]
                cpExmao.actionDrop(tile)
                # 广播其出牌
                for seatIndex in range(self.playerCount):
                    message = self.msgProcessor.table_call_drop(self.curSeat
                        , self.player[seatIndex]
                        , tile
                        , MTableState.TABLE_STATE_NEXT
                        , {}
                        , self.actionID
                        , 0)
                    ftlog.debug( 'MajiangTableLogic.extendMao, table_call_drop: mmessage' ,message)
                    self.msgProcessor.send_message(message, [self.player[seatIndex].userId])

        if checkPassDropPro or checkPassQiangExmaoPro:
            lastSeatId = self.curSeat
            cp.actionAdd(tile)
            cp.actionPeng(tile, pengPattern, self.actionID, lastSeatId)

            self.__cur_seat = cp.curSeatId
            self.incrActionId('pengTile')
            
            timeOut = self.__table_stater.getTimeOutByState(state)

            pengTingNotGrab = False
            if self.checkTableState(MTableState.TABLE_STATE_TING) and self.__ting_rule_mgr.canTingAfterPeng(cp.copyTiles()):
                _, tingArr = self.__ting_rule_mgr.canTing(cp.copyTiles(), self.tableTileMgr.tiles, tile, self.tableTileMgr.getMagicTiles(cp.isTing()), \
                                                                   self.__cur_seat, cp.curSeatId, self.actionID)
                if len(tingArr) > 0:
                    exInfo.appendInfo(MTableState.TABLE_STATE_TING, tingArr)
                    pengTingNotGrab = True
                    ftlog.debug( 'MajiangTable.pengTile seatId:', cp.curSeatId, ' can ting with peng (not grab ting)' )

            # 初始化处理器，抢听完了转听
            if (state & MTableState.TABLE_STATE_GRABTING) or pengTingNotGrab:
                self.addCardProcessor.initProcessor(self.actionID, MTableState.TABLE_STATE_TING, cp.curSeatId, tile, exInfo, timeOut)
                self.addCardProcessor.setMustTing(state & MTableState.TABLE_STATE_GRABTING)
            else:
                self.addCardProcessor.initProcessor(self.actionID, MTableState.TABLE_STATE_DROP, cp.curSeatId, tile, exInfo, timeOut)

            actionInfo = {}
            ting_action = None
            if state & MTableState.TABLE_STATE_GRABTING:
                tingInfo = exInfo.extend['pengTing'][0]
                ftlog.debug('pengTile grabTing tingInfo:', tingInfo)
                ting_action = exInfo.getGrabTingAction(tingInfo, seatId, self.tableTileMgr, True)
                actionInfo['ting_action'] = ting_action
            # 吃碰完能补杠
            if self.tableTileMgr.canGangAfterPeng():
                quemen = -1
                if self.checkTableState(MTableState.TABLE_STATE_ABSENCE): 
	            quemen = self.absenceProcessor.absenceColor[cp.curSeatId]
                gang = self.gangRuleMgr.hasGang(cp.copyTiles(), 0, state,quemen)
                if gang:
                    actionInfo['gang_action'] = gang
                pigus = self.tableTileMgr.getPigus()
                if pigus:
                    actionInfo['fanpigu_action'] = pigus

            # 判断锚/蛋牌
            if self.checkTableState(MTableState.TABLE_STATE_FANGMAO):
                maoInfo = {}
                if self.ifCalcFangDan(cp.curSeatId) and (not cp.isTing()):
                    isFirstAddtile = self.isFirstAddTile(cp.curSeatId)
                    maos = self.maoRuleMgr.hasMao(cp.copyHandTiles()
                                       , self.tableConfig.get(MTDefine.MAO_DAN_SETTING, MTDefine.MAO_DAN_NO)
                                       , cp.getMaoTypes(), isFirstAddtile
									   ,{"maoType":cp.getPengMaoTypes()})
                    if len(maos) > 0:
                        maoInfo['mao_tiles'] = maos

                if not cp.isTing():
                    extendMaos = self.maoRuleMgr.hasExtendMao(cp.copyHandTiles(), cp.getMaoTypes())
                    if len(extendMaos) > 0:
                        maoInfo['mao_extends'] = extendMaos

                if ('mao_tiles' in maoInfo) or ('mao_extends' in maoInfo):
                    exInfo.appendInfo(MTableState.TABLE_STATE_FANGMAO, maoInfo)

            # 判断补花
            if self.checkTableState(MTableState.TABLE_STATE_BUFLOWER):
                cp = self.player[seatId]
                flowers = self.flowerRuleMgr.hasFlower(cp.copyHandTiles())  # 手中剩余花牌
                if len(flowers)> 0:
                    if flowers[0] and self.flowerRuleMgr.isFlower(flowers[0]):
                        # 执行补花
                        cp.handTiles.remove(flowers[0])
                        cp.flowers.append(flowers[0])
                        self.tableTileMgr.setFlowerTileInfo(flowers[0], seatId)

                        # 累计花分
                        cp.addFlowerScores(1)
                        self.tableTileMgr.addFlowerScores(1, seatId)
                        self.msgProcessor.table_call_bu_flower_broadcast(seatId, flowers[0], cp.flowers,
                                                                         self.tableTileMgr.flowerScores(seatId),
                                                                         self.getBroadCastUIDs())
                        self.processAddTileSimple(cp)

            # 非抢听情况下，部分玩法如果能碰后听牌，需要马上听牌
            if pengTingNotGrab:
                ting_action_not_grab = exInfo.getTingResult(self.tableTileMgr, seatId)
                if ting_action_not_grab:
                    tingliang_action = exInfo.getTingLiangResult(self.tableTileMgr)
                    if tingliang_action:
                        actionInfo['tingliang_action'] = tingliang_action
                    kou_ting_action = exInfo.getCanKouTingResult(self.tableTileMgr, seatId)
                    if kou_ting_action:
                        actionInfo['kou_ting_action'] = kou_ting_action
                    #抢听把ting_action占用了，只能用ting_action_not_grab区分
                    actionInfo['ting_action_not_grab'] = ting_action_not_grab

            # 是否可以报警
            isCanAlarm = 0
            if self.getTableConfig(MTDefine.SWITCH_FOR_ALARM, 0):
                isCanAlarm = cp.canAlarm(cp.copyTiles(), tile)

            # 碰消息广播
            for player in self.player:
                self.__msg_processor.table_call_after_peng(lastSeatId
                        , self.curSeat
                        , tile
                        , timeOut
                        , self.actionID
                        , player
                        , pengPattern
                        , actionInfo
                        , exInfo)

                # 广播报警
                if isCanAlarm:
                    self.__msg_processor.table_call_alarm(seatId, player, isCanAlarm)

            self.changeMagicTileAfterChiPengExmao()

        if checkPassQiangExmaoPro:
            self.qiangExmaoPengProcessor.reset()
        else:
            ftlog.debug( 'pengTile error, need check....' )
            
    def zhanTile(self, seatId, tile, zhanPattern, state, special_tile):
        """粘别人的牌
        只有一个人，且只判断__drop_card_processor
        """
        cp = self.__players[seatId]
        if self.__drop_card_processor.updateProcessor(self.actionID, seatId, state, tile, zhanPattern):
            exInfo = self.__drop_card_processor.getExtendResultBySeatId(seatId)
            self.__drop_card_processor.reset()
            #cp.actionAdd(tile) 加入之后actionZhan还是要移除
            cp.actionZhan(tile, zhanPattern, self.actionID)
            lastSeatId = self.curSeat
            self.__cur_seat = cp.curSeatId
            self.incrActionId('zhanTile')
            
            timeOut = self.__table_stater.getTimeOutByState(state)
            # 初始化处理器，抢听完了转听
            if state & MTableState.TABLE_STATE_GRABTING:
                self.addCardProcessor.initProcessor(self.actionID, MTableState.TABLE_STATE_TING, cp.curSeatId, tile, exInfo, timeOut)
                self.addCardProcessor.setMustTing(state & MTableState.TABLE_STATE_GRABTING)
            else:
                self.addCardProcessor.initProcessor(self.actionID, MTableState.TABLE_STATE_DROP, cp.curSeatId, tile, exInfo, timeOut)
            
            ftlog.debug('after zhanTile init addCardProcessor state:', state
                    , ' curSeatId:', cp.curSeatId
                    , ' exInfo.extend:', exInfo.extend)
              
            actionInfo = {}
            ting_action = None
            if state & MTableState.TABLE_STATE_GRABTING:
                tingInfo = exInfo.extend['zhanTing'][0]
                ftlog.debug('zhanTile grabTing tingInfo:', tingInfo)
                ting_action = exInfo.getGrabTingAction(tingInfo, seatId, self.tableTileMgr, True)
                actionInfo['ting_action'] = ting_action
                             
            # 粘消息广播
            for player in self.player:
                self.__msg_processor.table_call_after_zhan(lastSeatId
                        , self.curSeat
                        , tile
                        , timeOut
                        , self.actionID
                        , player
                        , zhanPattern
                        , actionInfo)
            
        else:
            ftlog.debug( 'zhanTile error, need check....' )
    # 抢杠胡
    def grabHuGang(self, seatId, tile, wins=tuple()):
        if seatId not in wins:
            wins = (seatId,)

        if self.qiangGangHuProcessor.getState() == 0:
            return

        if self.qiangGangHuProcessor.updateDuoHu(self.actionID, wins, MTableState.TABLE_STATE_QIANGGANG) or \
                self.qiangGangHuProcessor.updateProcessor(self.actionID, seatId, MTableState.TABLE_STATE_QIANGGANG, tile, None):
            # 不用客户端传过来的这张牌
            tile = self.qiangGangHuProcessor.tile
            self.qiangGangHuProcessor.reset()
            # 和牌后，获取最后的特殊牌
            self.tableTileMgr.drawLastSpecialTiles(self.curSeat, seatId)

            # 从被抢杠者手牌里去掉这张牌
            if self.tableConfig.get(MTDefine.REMOVE_GRABBED_GANG_TILE, 1):
		ftlog.debug('MajiangTableLogic.grabHuGang remove tile') 
                self.players[self.curSeat].handTiles.remove(tile)
            looses = [self.curSeat]
            for winSeat in wins:
                winPlayer = self.player[winSeat]
                winPlayer.actionHuFromOthers(tile)
                if len(wins) > 1:
                    winPlayer.setXuezhanRank(self.getWinPlayerCount())
            if len(wins) > 1:
                loosePlayer = self.player[self.curSeat]
                loosePlayer.setXuezhanRank(-1)

            # 当前的座位号胡牌，胡牌类型为抢杠
            winBase = self.getTableConfig(MTDefine.WIN_BASE, 1)
            ftlog.debug('MajiangTableLogic.gameWin winBase: ', winBase)
            winMode = [MOneResult.WIN_MODE_LOSS for _ in range(self.playerCount)]
            fanPattern = [[] for _ in range(self.playerCount)]
            awardInfo = []
            awardScores = [0 for _ in range(self.playerCount)]
            currentScore = [0 for _ in range(self.playerCount)]
            piaoPoints = None
            flowerScores = None
            displayExtends = None
            moziScores = None  # 摸子分
            lianzhuangCount = None
	    cp = self.player[seatId]
            if winBase > 0:
                result = MOneResultFactory.getOneResult(self.playMode)
                result.setResultType(MOneResult.RESULT_WIN)
                result.setWinSeats(wins)
                result.setLastSeatId(self.curSeat)
                result.setWinSeatId(seatId)
                result.setQiangGang(True)
                result.setTableConfig(self.tableConfig)
                result.setBankerSeatId(self.queryBanker())
                result.setPlayerCount(self.playerCount)
                if self.checkTableState(MTableState.TABLE_STATE_TING):
                    result.setWinNodes(cp.winNodes)

                if self.getTableConfig(MTDefine.SWITCH_FOR_ALARM, 0):
                    result.setAlarmNodes(cp.alarmInfo)

                    jiaoPaiConf = self.getTableConfig("jiaopai_rule", {})
                    result.setJiaoPaiConf(jiaoPaiConf[str(self.__win_rule_mgr.multiple)])

                    fanRuleConf = self.getTableConfig("fan_rule", {})
                    result.setFanRuleConf(fanRuleConf[str(self.__win_rule_mgr.multiple)])

                tingState = [0 for _ in range(self.playerCount)]
                colorState = [0 for _ in range(self.playerCount)]
                menState = [0 for _ in range(self.playerCount)]
                ziState = [[0,0,0,0,0,0,0] for _ in range(self.playerCount)]
                playerAllTiles = [0 for _ in range(self.playerCount)]
                playerGangTiles = [0 for _ in range(self.playerCount)]
                playerScore = [0 for _ in range(self.playerCount)]
                for player in self.player:
                    # 听牌状态
                    if player.isTing():
                        tingState[player.curSeatId] = 1
                    # 花色状态    
                    pTiles = player.copyTiles()
                    tileArr = MTile.changeTilesToValueArr(MHand.copyAllTilesToList(pTiles))
                    colorState[player.curSeatId] = MTile.getColorCount(tileArr)
                    
                    #字
                    tempTiles = MTile.traverseTile(MTile.TILE_FENG)
                    ziState[player.curSeatId] = tileArr[tempTiles[0]:tempTiles[len(tempTiles)-1]+1]
                    # 玩家牌的情况
                    playerAllTiles[player.curSeatId] = player.copyTiles()
                    playerGangTiles[player.curSeatId] = player.copyGangArray()
                    # 门清状态
                    handTiles = player.copyHandTiles()
                    gangTiles = player.copyGangArray()
                    ming,an = MTile.calcGangCount(gangTiles)
                    if len(handTiles) == self.handCardCount-an*3:
                        menState[player.curSeatId] = 1

                    if self.tableConfig.get(MTDefine.OVER_BY_SCORE, 0):
                        curBaseCount = self.tableConfig[MFTDefine.CUR_BASE_COUNT]
                        playerScore[player.curSeatId] = player.getCurScoreByBaseCount(curBaseCount)

                result.setMenState(menState)
                result.setTingState(tingState)
                result.setDoublePoints(self.doubleProcessor.doublePoints)
                result.setColorState(colorState)
                result.setZiState(ziState)
                result.setPlayerAllTiles(playerAllTiles)
                result.setPlayerGangTiles(playerGangTiles)
                ftlog.debug("grabGangHuWinTile =",tile)
                result.setPlayerCurScore(playerScore)
                result.setWinTile(tile)
                result.setActionID(self.actionID)
                result.setTableTileMgr(self.tableTileMgr)
                result.setMultiple(self.__win_rule_mgr.multiple)
                result.setWinRuleMgr(self.winRuleMgr)
                result.setPiaoProcessor(self.piaoProcessor)
                result.calcScore()

                self.roundResult.setPlayMode(self.playMode)
                self.roundResult.addRoundResult(result)
                ftlog.debug('roundResult.addRoundResult 4')
                #加上牌桌上局数总分
                tableScore = [0 for _ in range(self.playerCount)]
                if self.tableResult.score:
                    tableScore = self.tableResult.score
                currentJiaoScore = [0 for _ in range(self.playerCount)]
                for i in range(self.playerCount):
                    currentScore[i] = tableScore[i] + self.roundResult.score[i]

                    if self.tableConfig.get(MTDefine.OVER_BY_SCORE, 0):
                        curBaseCount = self.tableConfig[MFTDefine.CUR_BASE_COUNT]
                        if result.isCountByJiao():
                            currentScore[i] = self.player[i].getCurScoreByBaseCount(curBaseCount)
                        elif result.isCountByTongDi():
                            currentScore[i] = self.player[i].getCurScoreByBaseCount(curBaseCount)
                        else:
                            # 如果不是交牌 当前积分就是玩家积分+本局输赢 更新玩家积分
                            currentScore[i] = self.player[i].getCurScoreByBaseCount(curBaseCount)+self.roundResult.score[i]
                            self.player[i].setScore(currentScore[i], curBaseCount)
                        currentJiaoScore[seatId] = self.player[i].getCurJiaoScoreByBaseCount(curBaseCount)

                self.msgProcessor.table_call_score(self.getBroadCastUIDs(), currentScore, self.roundResult.delta, currentJiaoScore)
                if MOneResult.KEY_WIN_MODE in result.results:
                    winMode = result.results[MOneResult.KEY_WIN_MODE] 

                #计算手牌杠
                self.calcGangInHand(-1,seatId, tile, playerAllTiles,result.winNodes)
		
                if MPlayMode().isSubPlayMode(self.playMode, MPlayMode.LUOSIHU):
                    fanPattern = self.roundResult.getMergeFanPatternList()
                else:
                    if MOneResult.KEY_FAN_PATTERN in result.results:
                        fanPattern = result.results[MOneResult.KEY_FAN_PATTERN]
                    #带上明杠暗杠oneResult中的番型信息
                    fanPattern = self.appendGangFanPattern(fanPattern)
		
                if MOneResult.KEY_AWARD_INFO in result.results:
                    awardInfo = result.results[MOneResult.KEY_AWARD_INFO]
                if MOneResult.KEY_AWARD_SCORE in result.results:
                    awardScores = result.results[MOneResult.KEY_AWARD_SCORE]
                if MOneResult.KEY_DISPLAY_EXTEND in result.results:
                    displayExtends = result.results[MOneResult.KEY_DISPLAY_EXTEND]
                if MOneResult.KEY_MOZI in result.results:
                    moziScores = result.results[MOneResult.KEY_MOZI]

	        if MOneResult.KEY_LIANZHUANG in result.results:
         	    lianzhuangCount = result.results[MOneResult.KEY_LIANZHUANG]

            # 清空之前的杠牌记录
            self.setLatestGangState(-1)
            self.__win_rule_mgr.setLastGangSeat(-1)
            ftlog.debug("gangTileclearLatestGangState = ", self.latestGangState)
            # 点炮和，一个人和，一个人输，其他两人游戏结束
            scoreBase = self.getTableConfig(MTDefine.SCORE_BASE, 0)
            uids = self.getBroadCastUIDs()
            observers = []
            for player in self.player:
                if (player.curSeatId not in wins) and (player.curSeatId not in looses):
                    observers.append(player.curSeatId)
		ftlog.debug('player.handTiles:',player.handTiles)
     		#modify by yj 05.06 移除被抢杠胡的牌
	        if player.curSeatId in looses:
                    if self.checkTableState(MTableState.TABLE_STATE_XUEZHAN) or self.checkTableState(MTableState.TABLE_STATE_XUELIU): 
                        self.msgProcessor.table_call_refresh_handtiles(player.userId, player.curSeatId,player.handTiles,tile) 
			self.processAddTile(player, MTableState.TABLE_STATE_NEXT)
			self.setCurSeat(player.curSeatId)
	    
	    #将胡牌加入门前牌堆，便于计算听牌剩余张数
            self.tableTileMgr.setHuTileInfo(tile) 
	    ftlog.debug('MajiangTableLogic.grabHuGang setMenTileInfo',self.curSeat,tile) 
	    
	    if self.isWinFinalOrFlow():
		self.__table_result.addResult(self.roundResult) 
            # 更新圈数
            self.calcQuan(self.__playerCount, 1, seatId)
            if self.checkTableState(MTableState.TABLE_STATE_XUEZHAN) or self.checkTableState(MTableState.TABLE_STATE_XUELIU): 
        	ftlog.debug('MajiangTableLogic.grabHugang not setCurSeat')    
	    else:
		self.setCurSeat(seatId)
		ftlog.debug('self.setCurSeat 9',seatId)
            # 抢杠和，局数不加1
            ctInfo = self.getCreateTableInfo()   
            btInfo, _ = self.getBaoPaiInfo()
            # 获取最后特殊牌的协议信息
            lstInfo = self.tableTileMgr.getLastSpecialTiles(self.bankerMgr.queryBanker())
            customInfo = {
                'ctInfo':ctInfo,
                'btInfo':btInfo,
                'lstInfo':lstInfo,
                'awardInfo':awardInfo,
                'awardScores':awardScores,
                'moziScores':moziScores,
                'lianzhuangCount':lianzhuangCount,
		'loseFinal':self.isWinFinalOrFlow(),
                'winFinal':self.isWinFinalOrFlow()           
   		 }

            scores = {}
            scores['totalScore'] = self.tableResult.score
            if self.tableConfig.get(MTDefine.OVER_BY_SCORE, 0):
                #总积分是玩家积分 不是输赢积分
                scores['totalScore'] = currentScore

            scores['deltaScore'] = self.roundResult.score
            scores['deltaGangScore'] = self.roundResult.getRoundGangResult()
            scores['deltaWinScore'] = self.roundResult.getRoundWinResult()
            self.setLastWins(wins)
            self.setLastLooses(looses)
            if not len(wins) > 1:
                if not (cp.xuezhanRank == -1):
                    cp.setXuezhanRank(self.getWinPlayerCount())
            self.msgProcessor.table_call_game_win_loose(uids
                    , wins
                    , looses
                    , observers
                    , winMode
                    , tile
                    , scores
                    , scoreBase
                    , fanPattern
                    , customInfo
                    , piaoPoints
                    ,flowerScores
                    , displayExtends
		    ,self.curSeat
                    ,self.isWinFinalOrFlow())
            # 判断和牌是否结束
            if len(wins) > 1:
                self.processHu(self.players[len(wins)-1])
            else:
                self.processHu(cp,True)


    # 潜江晃晃，三张赖子皮当作一个杠
    # 以style=6和7为区别，杠完直接打牌，且可以听
    def justGangThreeTile(self, lastSeatId, seatId, gangTile, gangPattern, style, state, afterAdd, special_tile = None, qiangGangSeats = [],tmpState=0):
        ftlog.debug('MTableLogic.justGangTile lastSeatId', lastSeatId,
                    'seatId:', seatId, ' gangTile:', gangTile,
                    'gangPattern:', gangPattern, 'style:', style, ' state:', state)
        # 牌局手牌管理器记录杠的数量
        self.tableTileMgr.incGangCount()

        #发送给客户端的结构
        gang = {}
        gang['tile'] = gangTile
        gang['pattern'] = gangPattern
        gang['style'] = style
        cp = self.player[seatId]
        #潜江晃晃的朝天笑，确认杠
        if style == MPlayerTileGang.CHAOTIANXIAO_MING:
            cp.actionAdd(gangTile)
        ftlog.info("justGangTileChaoTian:",lastSeatId,seatId,gangTile,state,afterAdd)
        cp.actionChaoTian(gangPattern,gangTile,self.actionID,style)
        cp.gangTilesFromSeat.append({'tile':gangPattern[0],'playerSeatId':lastSeatId})
        # 设置本次杠牌状态
        self.setLatestGangState(seatId)
        self.__win_rule_mgr.setLastGangSeat(seatId)
        ftlog.debug("gangTilesetLatestGangState = ", seatId)
        self.incrActionId('gangThreeTile')
        state=MTableState.TABLE_STATE_DROP
        exInfo=MTableStateExtendInfo()
        #判断是否能听
        tingResult, tingReArr = self.tingRule.canTing(cp.copyTiles(), self.tableTileMgr.tiles,gangTile, self.tableTileMgr.getMagicTiles(cp.isTing()), \
                                                              self.__cur_seat, cp.curSeatId, self.actionID)
        ftlog.debug( 'MajiangTableLogic.justGangThreeTile canTing result: ', tingResult, ' solution:', tingReArr, ' length: ', len(tingReArr) )
        if tingResult and len(tingReArr) > 0:
            # 可以听牌
            state = state | MTableState.TABLE_STATE_TING
            exInfo.appendInfo(MTableState.TABLE_STATE_TING, tingReArr)
        if lastSeatId == seatId:
            tiles = cp.copyTiles()
            quemen = -1
            if self.checkTableState(MTableState.TABLE_STATE_ABSENCE): 
	        quemen = self.absenceProcessor.absenceColor[cp.curSeatId]
            gangs = self.gangRuleMgr.hasGang(cp.copyTiles(), gangTile, MTableState.TABLE_STATE_NEXT,quemen)
            canGang=True
            for tmpGang in gangs:
                if tmpGang["tile"] == self.tableTileMgr.laizi:
                    canGang=False
                if canGang and cp.canGang(gang, True, tiles, gangTile, self.__win_rule_mgr, self.tableTileMgr.getMagicTiles(cp.isTing())):
                    state = state | MTableState.TABLE_STATE_GANG
                    exInfo.appendInfo(MTableState.TABLE_STATE_GANG, tmpGang)
        # 判断锚/蛋牌
        if self.checkTableState(MTableState.TABLE_STATE_FANGMAO):
            maoInfo = {}
            if self.ifCalcFangDan(cp.curSeatId) and (not cp.isTing()):
                isFirstAddtile = self.isFirstAddTile(cp.curSeatId)
                maos = self.maoRuleMgr.hasMao(cp.copyHandTiles()
                                   , self.tableConfig.get(MTDefine.MAO_DAN_SETTING, MTDefine.MAO_DAN_NO)
                                   , cp.getMaoTypes(), isFirstAddtile
								   , {"maoType":cp.getPengMaoTypes()})
                if len(maos) > 0:
                    maoInfo['mao_tiles'] = maos

            if not cp.isTing():
                extendMaos = self.maoRuleMgr.hasExtendMao(cp.copyHandTiles(), cp.getMaoTypes())
                if len(extendMaos) > 0:
                    maoInfo['mao_extends'] = extendMaos

            if ('mao_tiles' in maoInfo) or ('mao_extends' in maoInfo):
                exInfo.appendInfo(MTableState.TABLE_STATE_FANGMAO, maoInfo)

        # 判断补花
        if self.checkTableState(MTableState.TABLE_STATE_BUFLOWER):
            cp = self.player[seatId]
            flowers = self.flowerRuleMgr.hasFlower(cp.copyHandTiles())  # 手中剩余花牌
            if len(flowers) > 0:
                if flowers[0] and self.flowerRuleMgr.isFlower(flowers[0]):
                    # 执行补花
                    cp.handTiles.remove(flowers[0])
                    cp.flowers.append(flowers[0])
                    self.tableTileMgr.setFlowerTileInfo(flowers[0], seatId)

                    # 累计花分
                    cp.addFlowerScores(1)
                    self.tableTileMgr.addFlowerScores(1, seatId)
                    self.msgProcessor.table_call_bu_flower_broadcast(seatId, flowers[0], cp.flowers,
                                                                     self.tableTileMgr.flowerScores(seatId),
                                                                     self.getBroadCastUIDs())
                    self.processAddTileSimple(cp)

        timeOut=self.tableStater.getTimeOutByState(state)
        self.addCardProcessor.initProcessor(self.actionID, state, cp.curSeatId, gangTile, exInfo, timeOut)
        # 给所有人发送杠牌结果(只有结果 没有抢杠和信息)
        ftlog.debug('table_call_after_gang seatId = ', seatId, 'qiangGangSeats= ', qiangGangSeats)

        # 杠牌之后设置当前位置为杠牌人的位置
        self.__cur_seat = cp.curSeatId

        #记录杠牌得分
        gangBase = self.getTableConfig(MTDefine.GANG_BASE, 0)
        ftlog.debug('MajiangTableLogic.justGangTile gangBase: ', gangBase)

        if gangBase > 0:
            result = MOneResultFactory.getOneResult(self.playMode)
            result.setResultType(MOneResult.RESULT_GANG)
            result.setLastSeatId(lastSeatId)
            result.setWinSeatId(self.curSeat)
            result.setTableConfig(self.tableConfig)
            result.setTableTileMgr(self.tableTileMgr)
            # 杠牌算分时，需要找到杠牌时的actionId，杠本身+1，所以此处-1
            result.setActionID(self.actionID - 1)
            result.setPlayerCount(self.playerCount)
            result.setStyle(style)
            result.setMultiple(self.__win_rule_mgr.multiple)
            result.setPiaoProcessor(self.piaoProcessor)
            result.calcScore()

            if result.results.get(MOneResult.KEY_GANG_STYLE_SCORE, None):
                ftlog.debug('MajiangTableLogic.justGangTile add gang score to cp: ', result.results[MOneResult.KEY_GANG_STYLE_SCORE], ',actionID', self.actionID)
                # 杠牌算分时，需要找到杠牌时的actionId，杠本身+1，所以此处-1
                cp.addGangScore(self.actionID - 1, result.results[MOneResult.KEY_GANG_STYLE_SCORE])

            #设置牌局过程中的明杠和暗杠番型信息
            if result.isResultOK():
                self.roundResult.setPlayMode(self.playMode)
                self.roundResult.addRoundResult(result)
                #加上牌桌上局数总分
                tableScore = [0 for _ in range(self.playerCount)]
                if self.tableResult.score:
                    tableScore = self.tableResult.score
                currentScore = [0 for _ in range(self.playerCount)]
                for i in range(self.playerCount):
                    currentScore[i] = tableScore[i] + self.roundResult.score[i]
		for i in range(self.playerCount):
		    self.__gang_scores[self.curSeat][i]+=self.roundResult.delta[i]
                self.msgProcessor.table_call_score(self.getBroadCastUIDs(), currentScore, self.roundResult.delta)

        loser_coins = []
        real_win_coin = 0
	loser_seat_ids = []
        for i in range(self.playerCount):
            if self.roundResult.delta[i] < 0:
                loser_coins.append(-self.roundResult.delta[i])
                loser_seat_ids.append(i)
		real_win_coin -= self.roundResult.delta[i]
        for player in self.player:
            #if player.curSeatId not in qiangGangSeats:
            self.msgProcessor.table_call_after_gang(lastSeatId
                    , seatId
                    , gangTile
                    , loser_seat_ids
                    , loser_coins
                    , real_win_coin
                    , self.actionID
                    , player
                    , gang #此时的杠是三张牌的朝天笑
                    , exInfo1=exInfo)


    #不用检查抢杠和 直接杠牌 包含明杠和暗杠
    def justGangTile(self, lastSeatId, seatId, gangTile, gangPattern, style, state, afterAdd, special_tile = None, qiangGangSeats = []):
        ftlog.debug('MTableLogic.justGangTile lastSeatId', lastSeatId, 
                    'seatId:', seatId, ' gangTile:', gangTile, 
                    'gangPattern:', gangPattern, 'style:', style, ' state:', state)
        # 牌局手牌管理器记录杠的数量
        self.tableTileMgr.incGangCount()
        
        #发送给客户端的结构
        gang = {}
        gang['tile'] = gangTile
        gang['pattern'] = gangPattern
        gang['style'] = style
        cp = self.player[seatId]
        cp.curLianGangNum += 1  # 连杠次数+1
        if afterAdd:
            # 加入带赖子的补杠
            magicTiles = self.tableTileMgr.getMagicTiles()
            cp.actionGangByAddCard(gangTile, gangPattern, style, self.actionID, magicTiles)
        # after drop
        else:
            # 明杠
            cp.actionAdd(gangTile)
            cp.actionGangByDropCard(gangTile, gangPattern, self.actionID, lastSeatId)
        cp.gangTilesFromSeat.append({'tile':gangPattern[0],'playerSeatId':lastSeatId})

        #是否可以报警
        isCanAlarm = 0
        if self.getTableConfig(MTDefine.SWITCH_FOR_ALARM, 0):
            isCanAlarm = cp.canAlarm(cp.copyTiles(), gangTile)

        # 设置本次杠牌状态
        self.setLatestGangState(seatId)
        self.__win_rule_mgr.setLastGangSeat(seatId)
        ftlog.debug("gangTilesetLatestGangState = ", seatId)
        self.incrActionId('gangTile')

        # 给所有人发送杠牌结果(只有结果 没有抢杠和信息)
        # 杠牌之后设置当前位置为杠牌人的位置
        self.__cur_seat = cp.curSeatId
	
        #记录杠牌得分
        gangBase = self.getTableConfig(MTDefine.GANG_BASE, 0)
        ftlog.debug('MajiangTableLogic.justGangTile gangBase: ', gangBase)
        
        if gangBase > 0:
            result = MOneResultFactory.getOneResult(self.playMode)
            result.setResultType(MOneResult.RESULT_GANG)
            result.setLastSeatId(lastSeatId)
            result.setWinSeatId(self.curSeat)
            result.setTableConfig(self.tableConfig)
            result.setTableTileMgr(self.tableTileMgr)
            # 杠牌算分时，需要找到杠牌时的actionId，杠本身+1，所以此处-1
            result.setActionID(self.actionID - 1)
            result.setPlayerCount(self.playerCount)
            result.setStyle(style)
            result.setMultiple(self.__win_rule_mgr.multiple)
            result.setPiaoProcessor(self.piaoProcessor)
            result.calcScore()

            if result.results.get(MOneResult.KEY_GANG_STYLE_SCORE, None):
                ftlog.debug('MajiangTableLogic.justGangTile add gang score to cp: ', result.results[MOneResult.KEY_GANG_STYLE_SCORE], ',actionID', self.actionID)
                # 杠牌算分时，需要找到杠牌时的actionId，杠本身+1，所以此处-1
                cp.addGangScore(self.actionID - 1, result.results[MOneResult.KEY_GANG_STYLE_SCORE])

            #设置牌局过程中的明杠和暗杠番型信息
            if result.isResultOK():
                self.roundResult.setPlayMode(self.playMode)
                self.roundResult.addRoundResult(result)
                ftlog.debug('roundResult.addRoundResult 6')
		#加上牌桌上局数总分
                tableScore = [0 for _ in range(self.playerCount)]
                if self.tableResult.score:
                    tableScore = self.tableResult.score
                currentScore = [0 for _ in range(self.playerCount)]
                for i in range(self.playerCount):
                    currentScore[i] = tableScore[i] + self.roundResult.score[i]
                for i in range(self.playerCount):
                    self.__gang_scores[self.curSeat][i]+=self.roundResult.delta[i]  
		self.msgProcessor.table_call_score(self.getBroadCastUIDs(), currentScore, self.roundResult.delta)
	
        loser_coins = []
        real_win_coin = 0
        loser_seat_ids = []
	 
	for i in range(self.playerCount):
	    if self.roundResult:
            	if self.roundResult.delta[i] < 0:
                    loser_coins.append(-self.roundResult.delta[i])
		    loser_seat_ids.append(i)
                    real_win_coin -= self.roundResult.delta[i]
	
        for player in self.player:
            #if player.curSeatId not in qiangGangSeats:
            self.msgProcessor.table_call_after_gang(lastSeatId
                    , seatId
                    , gangTile
                    , loser_seat_ids
                    , loser_coins
                    , real_win_coin
                    , self.actionID
                    , player
                    , gang)
	
        #    # 广播报警
            if isCanAlarm:
                self.msgProcessor.table_call_alarm(seatId, player, isCanAlarm)

        # 杠完上牌，应该先算杠分，后上牌。因为上牌后可能再杠或者和了，这样算分就乱了
        self.processAddTile(cp, state, special_tile, {"lastSeatId": lastSeatId, "seatId": seatId})
        
    def gangTile(self, seatId, tile, gangPattern, style, state, special_tile = None):
        """杠别人的牌
        只有一个人
        """
        ftlog.debug('MajiangTableLogic.gangTile seatId:', seatId
                    , ' tile:', tile
                    , ' gangPattern:', gangPattern
                    , ' style:', style
                    , ' self.addCardProcessor.getState:',self.addCardProcessor.getState()
                    , ' self.qiangGangHuProcessor.getState:', self.qiangGangHuProcessor.getState())
        lastSeatId = self.curSeat
        #发送给客户端的结构
        gang = {}
        gang['tile'] = tile
        gang['pattern'] = gangPattern
        gang['style'] = style

        if self.addCardProcessor.getState() != 0:
            # 如果是明杠，判断其他玩家是否可以抢杠和
            # 如果没有玩家抢杠和，给当前玩家发牌
            # 如果有玩家抢杠和，等待改玩家的抢杠和结果
            # 检测抢杠和
            qiangGangWin = False
            winSeats = [-1 for _ in range(self.playerCount)]
            canQiangGang = False
            if style == MPlayerTileGang.MING_GANG:
                canQiangGang = True

            ftlog.debug('MajiangTableLogic.gangTile after gang, canQiangGang===:', canQiangGang
                        , ' check state MTableState.TABLE_STATE_QIANGGANG:', self.checkTableState(MTableState.TABLE_STATE_QIANGGANG)
                        , ' check state MTableState.TABLE_STATE_HU:', self.checkTableState(MTableState.TABLE_STATE_HU))

            if canQiangGang and self.checkTableState(MTableState.TABLE_STATE_QIANGGANG) and self.checkTableState(MTableState.TABLE_STATE_HU):
                rulePass = False
                rule = self.tableTileMgr.qiangGangRule
                if lastSeatId == seatId:
                    # 自己出牌自己杠
                    # 暗杠0x001
                    # 补杠0x010
                    if style == MPlayerTileGang.AN_GANG and rule & MTableTile.QIANG_GANG_RULE_AN:
                        rulePass = True
                    elif style == MPlayerTileGang.MING_GANG and rule & MTableTile.QIANG_GANG_RULE_HUI_TOU:
                        rulePass = True
                else:
                    if style == MPlayerTileGang.MING_GANG and rule & MTableTile.QIANG_GANG_RULE_OTHER:
                    # 杠别人的牌0x100
                        rulePass = True
                            
                playerAllTiles = {}

                for index in range(1, self.playerCount):
                    newSeatId = (seatId + index) % self.playerCount
                    # 判断是否抢杠和牌
                    player = self.player[newSeatId]
                    magics = self.tableTileMgr.getMagicTiles(player.isTing())
                    # 红中宝不能抢杠胡
                    checkTile = gangPattern[-1]    
                    pTiles = player.copyTiles()
                    pTiles[MHand.TYPE_HAND].append(checkTile)
                    #modify by youjun 04.28
		    winResult = False
		    winMode = 0
                    if self.checkTableState(MTableState.TABLE_STATE_ABSENCE):
                        absenceColor = self.absenceProcessor.absenceColor[player.curSeatId]
                        tileArr = MTile.changeTilesToValueArr(player.handTiles)
                        if MTile.getTileCountByColor(tileArr, absenceColor) > 0:
                            winResult = False
                        else:
                            winResult, winPattern,_ = self.__win_rule_mgr.isHu(pTiles, gangPattern[-1], player.isTing(), MWinRule.WIN_BY_QIANGGANGHU, magics, player.winNodes, \
                                                         self.__cur_seat, player.curSeatId, self.actionID, False)
                            ftlog.debug( 'MajiangTable.gangTile after gang, check qiangGangHu winResult:', winResult
                                         , ' winPattern:', winPattern ) 
		    else:
		        winResult, winPattern,winMode = self.__win_rule_mgr.isHu(pTiles, gangPattern[-1], player.isTing(), MWinRule.WIN_BY_QIANGGANGHU, magics, player.winNodes, \
                                                     self.__cur_seat, player.curSeatId, self.actionID, False)
                        ftlog.debug( 'MajiangTable.gangTile after gang, check qiangGangHu winResult:', winResult
                                     , ' winPattern:', winPattern )
		    if MPlayMode().isSubPlayMode(self.playMode, MPlayMode.QUESHOU):
                        player.setWinMode(winMode)
                    if self.checkTableState(MTableState.TABLE_STATE_XUEZHAN) and player.isWon():
                        winResult = False                    
                    if winResult and rulePass:
                        # 可以和，给用户和的选择
                        state = MTableState.TABLE_STATE_QIANGGANG
                        winInfo = {}
                        winInfo['tile'] = tile
                        winInfo['qiangGang'] = 1
			if MPlayMode().isSubPlayMode(self.playMode, MPlayMode.QUESHOU):
	                    winInfo['winMode'] = winMode
                        winInfo['gangSeatId'] = self.curSeat
                        exInfo = MTableStateExtendInfo()
                        exInfo.appendInfo(state, winInfo)
                        ftlog.debug( 'MajiangTableLogic.gangTile after gang, qiangGangHu extendInfo:', exInfo )
                        timeOut = self.__table_stater.getTimeOutByState(state)
                        qiangGangWin = True
                        winSeats[player.curSeatId] = player.curSeatId
                     
                        self.qiangGangHuProcessor.initProcessor(self.actionID
                                , player.curSeatId
                                , state
                                , exInfo
                                , timeOut)
                        
            if qiangGangWin:
                self.qiangGangHuProcessor.initTile(tile, self.curSeat, state, gangPattern, style, special_tile)
                # 给自己发送杠牌结果
		
                for player in self.player:
                    if player.curSeatId in winSeats:
                        self.msgProcessor.table_call_after_gang(lastSeatId
                            , self.curSeat
                            , tile
                            , [lastSeatId]
                            , None
			    , None
			    , self.actionID
                            , player
                            , gang
                            , self.qiangGangHuProcessor.getExtendResultBySeatId(player.curSeatId))
		
                # 如果抢杠胡,需要给客户端发送屁股牌消息,让客户端关闭界面
                if self.checkTableState(MTableState.TABLE_STATE_FANPIGU):
                    pigus = self.tableTileMgr.getPigus()
                    self.msgProcessor.table_call_fanpigu(pigus, self.getBroadCastUIDs())  
                for player in self.player:
                    if player.curSeatId in winSeats:
                        if self.__win_rule_mgr.canDirectHuAfterTing() and player.isTing():
                       	    #直接和牌
                            self.grabHuGang(player.curSeatId, tile)
                return


            elif style in [MPlayerTileGang.CHAOTIANXIAO_MING,MPlayerTileGang.CHAOTIANXIAO_AN]:
                self.justGangThreeTile(lastSeatId, seatId, tile, gangPattern, style, state, True, special_tile)
            else:
                #直接杠牌
                self.justGangTile(lastSeatId, seatId, tile, gangPattern, style, state, True, special_tile)    
        elif self.__drop_card_processor.getState() != 0:
            if self.__drop_card_processor.updateProcessor(self.actionID, seatId, state, tile, gang):
                self.__drop_card_processor.reset()
                if style in [MPlayerTileGang.CHAOTIANXIAO_MING,MPlayerTileGang.CHAOTIANXIAO_AN]:
                    self.justGangThreeTile(lastSeatId, seatId, tile, gangPattern, style, state, False, special_tile)
                else:
                    #直接杠牌
                    self.justGangTile(lastSeatId, seatId, tile, gangPattern, style, state, False, special_tile)
        elif self.qiangExmaoPengProcessor.getState() != 0:
            checkPassQiangExmaoPro = self.qiangExmaoPengProcessor.updateProcessor(self.actionID, seatId, MTableState.TABLE_STATE_GANG, tile, gangPattern)
            if checkPassQiangExmaoPro:
                cpExmao = self.player[self.qiangExmaoPengProcessor.curSeatId]
                cpExmao.actionDrop(tile)
                # 广播其出牌
                for seatIndex in range(self.playerCount):
                    # 已经向exmaoSeatId广播过出牌了
                    if seatIndex == self.qiangExmaoPengProcessor.exmaoSeatId:
                        continue

                    message = self.msgProcessor.table_call_drop(self.curSeat
                        , self.player[seatIndex]
                        , tile
                        , MTableState.TABLE_STATE_NEXT
                        , {}
                        , self.actionID
                        , 0)
                    ftlog.debug( 'MajiangTableLogic.extendMao, table_call_drop: mmessage' ,message)
                    self.msgProcessor.send_message(message, [self.player[seatIndex].userId])
                self.qiangExmaoPengProcessor.reset()
                #直接杠牌
                self.justGangTile(lastSeatId, seatId, tile, gangPattern, style, state, False, special_tile)

    def changeToTingState(self, player, tile):
        # 判断听牌
        allTiles = player.copyTiles()
        if not player.isTing():
            """切换到听牌状态，这个时候，获取听牌方案，是一定可以取到的，取不到就有问题"""
            tingResult, tingReArr = self.tingRule.canTing(allTiles, self.tableTileMgr.tiles, tile, self.tableTileMgr.getMagicTiles(player.isTing()), \
                                                          self.__cur_seat, player.curSeatId, self.actionID)
            if tingResult and len(tingReArr) > 0:
                # 可以听牌
                ftlog.debug( 'MajiangTableLogic.changeToTingState canTing result value: ', tingResult, ' result array: ', tingReArr )
                exInfo = MTableStateExtendInfo()
                exInfo.setInfo(MTableState.TABLE_STATE_TING, tingReArr)
                return True, exInfo
            else:
                ftlog.debug( 'error, player can not ting!!!!! seatId:', player.curSeatId )
        else:
            ftlog.debug( 'error, player already ting! seatId:', player.curSeatId )
        
        return False, None

    def addZFBGang(self,winSeatId):
        result = MOneResultFactory.getOneResult(self.playMode)
        result.setResultType(MOneResult.RESULT_GANG)
        result.setStyle(MPlayerTileGang.ZFB_GANG)
        result.setLastSeatId(winSeatId)
        result.setWinSeatId(winSeatId)
        result.setPlayerCount(self.playerCount)
        result.setTableConfig(self.tableConfig)
        result.calcScore()
        if result.isResultOK():
            self.roundResult.setPlayMode(self.playMode)
            self.roundResult.addRoundResult(result)
	    ftlog.debug('roundResult.addRoundResult 8')

    def calcGangInHand(self,winSeatId,lastSeatId,winTile,alltiles,winNodes):
        ftlog.debug('MBaichengOneResult calcGangInHand winSeatId:',winSeatId,'self.playerCount',self.playerCount)

    def gameWin(self, seatId, tile, wins = [],qiangjinState = 0,isSanJinDao = False):
        """
        胡牌
        1）出牌时 可以有多个人和牌
        2）摸牌时，只有摸牌的人和牌
        """
        lastSeatId = self.curSeat
	cp = self.player[seatId]
        tingState = [0 for _ in range(self.playerCount)]
        for player in self.player:
            # 听牌状态
            if player.isTing():
                tingState[player.curSeatId] = 1
	# 和牌后，获取最后的特殊牌
        self.tableTileMgr.drawLastSpecialTiles(lastSeatId, seatId)
        # 结算的类型
        # 1 吃和
        # 0 自摸
        # -1 输牌
        if seatId not in wins:
            wins = [seatId]
        ftlog.debug( 'MajiangTableLogic.gameWin seatId:', seatId
                     , ' lastSeatId:', lastSeatId
                     , ' wins:', wins)

        looses = []
        observers = []
        gangKai = False
        gangKaiLastSeatId = -1
        gangKaiSeatId = -1
        daFeng = False
        baoZhongBao = False
        huaCi = False
        magicAfertTing = False
        tianHu = False
        wuDuiHu = False
        winNode = None
        shuangdahuMark=0
	sanjindao = False
        if self.addCardProcessor.getState() != 0:
            ftlog.debug('MajiangTableLogic.gameWin process by addCardProcessor...')
            exInfo = self.addCardProcessor.extendInfo
            winNode = exInfo.getWinNodeByTile(tile)
            if winNode and ('gangKai' in winNode) and winNode['gangKai']:
                gangKai = True
                gangKaiLastSeatId = winNode.get('lastSeatId', -1)
                gangKaiSeatId = winNode.get('seatId', -1)
            if winNode and ('baoZhongBao' in winNode) and winNode['baoZhongBao']:
                baoZhongBao = True 
            if winNode and ('tianHu' in winNode) and winNode['tianHu']:
                tianHu = True 
            if winNode and ('wuDuiHu' in winNode) and winNode['wuDuiHu']:
                wuDuiHu = True
            if winNode and ('huaCi' in winNode) and winNode['huaCi']:
                huaCi = True
            ftlog.debug('table_logic gameWin winNode:', winNode)
            self.addCardProcessor.updateProcessor(self.actionID, MTableState.TABLE_STATE_HU, seatId)
	    if self.curSeat == seatId:
                cp.actionHuByMyself(tile,not (baoZhongBao or tianHu or wuDuiHu or isSanJinDao))
            else:
                cp.actionHuFromOthers(tile)
            #cp.actionHuByMyself(tile, not (baoZhongBao or tianHu or wuDuiHu or isSanJinDao))
            # 自摸，一个人和，其他人都输
            for player in self.player:
                if player.curSeatId != seatId:
                    #modify by youjun 05.04 血战已和牌玩家不计分
                    if self.checkTableState(MTableState.TABLE_STATE_XUEZHAN):
			if not player.isWon():
                            looses.append(player.curSeatId)
                    else:
                        looses.append(player.curSeatId)
        elif self.dropCardProcessor.getState() != 0:
            ftlog.debug('MajiangTableLogic.gameWin process by dropCardProcessor...')
            winState = MTableState.TABLE_STATE_HU
            if self.dropCardProcessor.updateDuoHu(self.actionID, wins, winState) or \
                self.dropCardProcessor.updateProcessor(self.actionID, seatId, winState, tile, None):
                self.louHuProcesssor.reset()
                if winState & MTableState.TABLE_STATE_HU:
                    self.dropCardProcessor.reset()
                    if MPlayMode().isSubPlayMode(self.playMode, MPlayMode.QUESHOU) and len(wins) > 1:
                        bestWinResult,bestWinner = self.calcBestWinner(wins,False)
                        if bestWinResult:
                            wins = bestWinner
                    for winSeat in wins:
                        winPlayer = self.player[winSeat]
                        winPlayer.actionHuFromOthers(tile)
                        if len(wins) > 1:
                            winPlayer.setXuezhanRank(self.getWinPlayerCount())
                            ftlog.debug('MajiangTableLogic.gameWin winPlayer xuezhanRank:',winPlayer.xuezhanRank,' seatId:',winPlayer.curSeatId)
                    looses.append(lastSeatId)
                    if len(wins) > 1:
                        loosePlayer = self.player[lastSeatId]
                        loosePlayer.setXuezhanRank(-1)
                    for player in self.player:
                        if (player.curSeatId not in wins) and (player.curSeatId not in looses):
                            observers.append(player.curSeatId)
            else:
                # 有上家同时和牌 那么当前玩家不给予响应 除非上家过牌
                return
        elif self.louHuProcesssor.getState() != 0:
            ftlog.debug('MajiangTableLogic.gameWin process by louHuProcesssor...')
            winState = MTableState.TABLE_STATE_PASS_HU
            if self.louHuProcesssor.updateProcessor(self.actionID, MTableState.TABLE_STATE_PASS_HU, seatId):
                magicAfertTing = True
                winState = MTableState.TABLE_STATE_PASS_HU
                magicAfertTing = True
                exInfo = self.louHuProcesssor.extendInfo
                winNode = exInfo.getWinNodeByTile(tile)
                if winNode and ('baoZhongBao' in winNode) and winNode['baoZhongBao']:
                    baoZhongBao = True    
                cp.actionAdd(tile) 
                cp.actionHuByMyself(tile, not baoZhongBao)
                # 自摸，一个人和，其他人都输
                for player in self.player:
                    if player.curSeatId != seatId:
                  	#modify by youjun 05.04 血战已和牌玩家不计分
                        if self.checkTableState(MTableState.TABLE_STATE_XUEZHAN):
			    if not player.isWon():
                                looses.append(player.curSeatId)
                        else:
                            looses.append(player.curSeatId)                
		self.louHuProcesssor.reset()
        elif self.daFengProcessor.getState() != 0:
            ftlog.debug('MajiangTableLogic.gameWin process by daFengProcessor...')
            if self.daFengProcessor.updateProcessor(self.actionID, MTableState.TABLE_STATE_HU, seatId):
                daFeng = True
                cp.actionHuByMyself(tile, True)
                # 自摸，一个人和，其他人都输
                for player in self.player:
                    if player.curSeatId != seatId:
                        #modify by youjun 05.04 血战已和牌玩家不计分
                        if self.checkTableState(MTableState.TABLE_STATE_XUEZHAN):
			    if not player.isWon():
                                looses.append(player.curSeatId)
                        else:
                            looses.append(player.curSeatId) 
                self.daFengProcessor.reset()
        elif self.qiangExmaoHuProcessor.getState() != 0:
            ftlog.debug('MajiangTableLogic.gameWin process by qiangExmaoHuProcessor...')
            if self.qiangExmaoHuProcessor.updateProcessor(self.actionID, seatId, MTableState.TABLE_STATE_QIANG_EXMAO_HU, tile, None):
                #补锚的那个人被抢胡，所以补锚的那个人弃牌
                cpExmao = self.player[self.qiangExmaoHuProcessor.curSeatId]
                cpExmao.actionDrop(tile)
                # 广播其出牌
                for seatIndex in range(self.playerCount):
                    message = self.msgProcessor.table_call_drop(self.curSeat
                        , self.player[seatIndex]
                        , tile
                        , MTableState.TABLE_STATE_NEXT
                        , {}
                        , self.actionID
                        , 0)
                    ftlog.debug( 'MajiangTableLogic.extendMao, table_call_drop: mmessage' ,message)
                    self.msgProcessor.send_message(message, [self.player[seatIndex].userId])
                
                ftlog.debug('MajiangTableLogic.gameWin qiangExmaoHuProcessor.updateProcessor')
                self.qiangExmaoHuProcessor.reset()
                cp.actionHuFromOthers(tile)
                looses.append(lastSeatId)
                for player in self.player:
                    if (player.curSeatId not in wins) and (player.curSeatId not in looses):
                        observers.append(player.curSeatId)
            else:
                # 有上家同时和牌 那么当前玩家不给予响应 除非上家过牌
                return
	elif self.curState() == MTableState.TABLE_STATE_DROP:
            for winSeat in wins:
                winPlayer = self.player[winSeat]
		if self.curSeat == seatId:
	            winPlayer.actionHuByMyself(tile)
		else:
		    winPlayer.actionHuFromOthers(tile)
            for player in self.player:
                if player.curSeatId != seatId:
		    looses.append(player.curSeatId)

	    ftlog.debug('MajiangTableLogic.gameWin:xxx',self.curState())
        else:
            for winSeat in wins:
                winPlayer = self.player[winSeat]
		if self.curSeat == seatId:
	            winPlayer.actionHuByMyself(tile)
		else:
                    winPlayer.actionHuFromOthers(tile)
            for player in self.player:
                if player.curSeatId != seatId:
                    looses.append(player.curSeatId)
	    ftlog.debug('MajiangTableLogic.gameWin:',self.curState())
            return

        if self.checkTableState(MTableState.TABLE_STATE_XUELIU):
            canTing, winNodes = self.canTingBeforeAddTile(cp.copyTiles(), self.tableTileMgr.tiles,self.tableTileMgr.getMagicTiles(cp.isWon()))
            if canTing:
                cp.setWinNodes(winNodes[0]['winNodes'])
                ftlog.debug('MajiangTableLogic.gameWin winNodes',winNodes)
                            
        self.incrActionId('gameWin')
	#queshou 一炮多响番型最大的胡牌
	if seatId in wins:
	    if self.playMode != 'luosihu-luosihu':
	        self.setCurSeat(seatId)
	else:
	    self.setCurSeat(wins[0])
        ftlog.debug('self.setCurSeat 10',seatId)
	# 记录杠牌得分
        winBase = self.getTableConfig(MTDefine.WIN_BASE, 1)
        ftlog.debug('MajiangTableLogic.gameWin winBase: ', winBase
                    , ' wins:', wins
                    , ' looses:', looses
                    , ' observers:', observers)
        
        winMode = [MOneResult.WIN_MODE_LOSS for _ in range(len(self.player))]
        fanPattern = [[] for _ in range(len(self.player))]
        awardInfo = []
        awardScores = [0 for _ in range(len(self.player))]
        currentScore = [0 for _ in range(self.playerCount)]
        piaoPoints = None
        flowerScores = None
        NeedDropTiles = False
        displayExtends = None
        moziScores = None
        lianzhuangCount = None

	if winBase > 0:
            result = MOneResultFactory.getOneResult(self.playMode)
            result.setResultType(MOneResult.RESULT_WIN)
            result.setLastSeatId(lastSeatId)
            result.setWinSeats(wins)
            result.setWinSeatId(self.curSeat)
            result.setLatestGangState(self.latestGangState)
            result.setTableConfig(self.tableConfig)
            result.setBankerSeatId(self.queryBanker())
            result.setHuaCi(huaCi)
            result.setGangKai(gangKai)
            result.setGangKaiLastSeatId(gangKaiLastSeatId)
            result.setGangKaiSeatId(gangKaiSeatId)
            result.setBaoZhongBao(baoZhongBao)
            result.setMagicAfertTing(magicAfertTing)
            result.setMagics(self.tableTileMgr.getMagicTiles(True))
            result.setTianHu(tianHu)
            result.setWuDuiHu(wuDuiHu)
            result.setPlayerCount(self.playerCount)
            if self.checkTableState(MTableState.TABLE_STATE_TING):
                result.setWinNodes(cp.winNodes)

            if self.checkTableState(MTableState.TABLE_STATE_XUELIU):
                ftlog.debug('MajiangTableLogic.gameWin winNodes',cp.winNodes)

            if self.getTableConfig(MTDefine.SWITCH_FOR_ALARM, 0):
                result.setAlarmNodes(cp.alarmInfo)

                jiaoPaiConf = self.getTableConfig("jiaopai_rule", {})
                result.setJiaoPaiConf(jiaoPaiConf[str(self.__win_rule_mgr.multiple)])

                fanRuleConf = self.getTableConfig("fan_rule", {})
                result.setFanRuleConf(fanRuleConf[str(self.__win_rule_mgr.multiple)])

            colorState = [0 for _ in range(self.playerCount)]
            menState = [0 for _ in range(self.playerCount)]
            ziState = [[0,0,0,0,0,0,0] for _ in range(self.playerCount)]
            mingState = [0 for _ in range(self.playerCount)]
            playerAllTiles = [0 for _ in range(self.playerCount)]
            playerHandTiles = [0 for _ in range(self.playerCount)]
            playerGangTiles = [0 for _ in range(self.playerCount)]
            playerScore = [0 for _ in range(self.playerCount)]
            for player in self.player:
                # 花色状态    
                pTiles = player.copyTiles()
                tileArr = MTile.changeTilesToValueArr(MHand.copyAllTilesToList(pTiles))
                colorState[player.curSeatId] = MTile.getColorCount(tileArr)
                tempTiles = MTile.traverseTile(MTile.TILE_FENG)
                ziState[player.curSeatId] = tileArr[tempTiles[0]:tempTiles[len(tempTiles)-1]+1]
                # 玩家牌的情况
                playerAllTiles[player.curSeatId] = player.copyTiles()
                playerHandTiles[player.curSeatId] = player.copyHandTiles()
                playerGangTiles[player.curSeatId] = player.copyGangArray()
                # 门清状态
                gangTiles = player.copyGangArray()
                ming,an = MTile.calcGangCount(gangTiles)
                ftlog.debug('MajiangTableLogic.gameWin calcMenState: seatId', player.curSeatId
                            , ' handTilesCount:', len(playerHandTiles[player.curSeatId])
                            , ' anGangCount:', an)
                if len(playerHandTiles[player.curSeatId]) == self.handCardCount-an*3:
                    menState[player.curSeatId] = 1
                # 明牌状态
                if player.isMing():
                    mingState[player.curSeatId] = 1

                if self.tableConfig.get(MTDefine.OVER_BY_SCORE, 0):
                    curBaseCount = self.tableConfig[MFTDefine.CUR_BASE_COUNT]
                    playerScore[player.curSeatId] = player.getCurScoreByBaseCount(curBaseCount)

            result.setMenState(menState)
            result.setTingState(tingState)
            result.setDoublePoints(self.doubleProcessor.doublePoints)
            result.setColorState(colorState)
            result.setZiState(ziState)
            result.setMingState(mingState)
            result.setPlayerAllTiles(playerAllTiles)
            result.setPlayerGangTiles(playerGangTiles)
            result.setPlayerCurScore(playerScore)
            result.setWinTile(tile)
            result.setActionID(self.actionID)
            result.setDaFeng(daFeng)
            result.setTableTileMgr(self.tableTileMgr)
            result.setWinRuleMgr(self.winRuleMgr)
            result.setMultiple(self.__win_rule_mgr.multiple)
            result.setPiaoProcessor(self.piaoProcessor)
            result.setActionID(self.actionID)
	    if qiangjinState and MPlayMode().isSubPlayMode(self.playMode, MPlayMode.QUESHOU):
                result.calcScore(qiangjinState)
            else:
                result.calcScore()
            self.setLatestGangState(-1)
            self.__win_rule_mgr.setLastGangSeat(-1)
            if result.dropHuFlag == 1:
                NeedDropTiles = True
            self.roundResult.setPlayMode(self.playMode)
            self.roundResult.addRoundResult(result)

            #计算手牌杠
            self.calcGangInHand(seatId,lastSeatId,tile,playerAllTiles,result.winNodes)
            #加上牌桌上局数总分
            tableScore = [0 for _ in range(self.playerCount)]
            if self.tableResult.score:
		#modify by youjun 05.04
           	tableScore = self.tableResult.score 
            currentJiaoScore = [0 for _ in range(self.playerCount)]
            for i in range(self.playerCount):
                currentScore[i] = tableScore[i] + self.roundResult.score[i]
                if self.tableConfig.get(MTDefine.OVER_BY_SCORE, 0):
                    curBaseCount = self.tableConfig[MFTDefine.CUR_BASE_COUNT]
                    if result.isCountByJiao():
                        currentScore[i] = self.player[i].getCurScoreByBaseCount(curBaseCount)
                    elif result.isCountByTongDi():
                        currentScore[i] = self.player[i].getCurScoreByBaseCount(curBaseCount)
                    else:
                        # 如果不是交牌 当前积分就是玩家积分+本局输赢 更新玩家积分
                        currentScore[i] = self.player[i].getCurScoreByBaseCount(curBaseCount)+self.roundResult.delat[i]
                        self.player[i].setScore(currentScore[i], curBaseCount)
                    currentJiaoScore[seatId] = self.player[i].getCurJiaoScoreByBaseCount(curBaseCount)
	    #modify by youjun 04.25
            self.msgProcessor.table_call_score(self.getBroadCastUIDs(), currentScore, self.roundResult.delta, currentJiaoScore)
            if MOneResult.KEY_WIN_MODE in result.results:
                winMode = result.results[MOneResult.KEY_WIN_MODE]
            
	    if MPlayMode().isSubPlayMode(self.playMode, MPlayMode.LUOSIHU):
                fanPattern = self.roundResult.getMergeFanPatternList()
            else:
                if MOneResult.KEY_FAN_PATTERN in result.results:
                    fanPattern = result.results[MOneResult.KEY_FAN_PATTERN]
                #带上明杠暗杠oneResult中的番型信息
                fanPattern = self.appendGangFanPattern(fanPattern)
	    

            if MOneResult.KEY_AWARD_INFO in result.results:
                    awardInfo = result.results[MOneResult.KEY_AWARD_INFO]
            if MOneResult.KEY_AWARD_SCORE in result.results:
                    awardScores = result.results[MOneResult.KEY_AWARD_SCORE]
            if MOneResult.KEY_DISPLAY_EXTEND in result.results:
                displayExtends = result.results[MOneResult.KEY_DISPLAY_EXTEND]
            if MOneResult.KEY_MOZI in result.results:
                moziScores = result.results[MOneResult.KEY_MOZI]

            if MOneResult.KEY_LIANZHUANG in result.results:
                lianzhuangCount = result.results[MOneResult.KEY_LIANZHUANG]
	
        #将胡牌加入门前牌堆，便于计算听牌剩余张数
        self.tableTileMgr.setHuTileInfo(tile) 
	ftlog.debug('MajiangTableLogic.gameWin setMenTileInfo',self.curSeat,tile)
	
        # 点炮和，一个人和，一个人输，其他两人游戏结束
	if self.isWinFinalOrFlow():
	    ftlog.debug('MajiangTableLogic.gameWin winFinal',self.isWinFinalOrFlow(),self.roundResult)
            self.__table_result.addResult(self.roundResult)
        scoreBase = self.getTableConfig(MTDefine.SCORE_BASE, 0)
        uids = self.getBroadCastUIDs()
        
        # 更新圈数 
        self.calcQuan(self.__playerCount, 1 ,seatId)
            
        ctInfo = self.getCreateTableInfo()
        btInfo, _ = self.getBaoPaiInfo() 
        # 获取最后特殊牌的协议信息
        lstInfo = self.tableTileMgr.getLastSpecialTiles(self.bankerMgr.queryBanker())
	customInfo = {
            'ctInfo':ctInfo,
            'btInfo':btInfo,
            'lstInfo':lstInfo,
            'awardInfo':awardInfo,
            'awardScores':awardScores,
            'moziScores':moziScores,
	    'lianzhuangCount':lianzhuangCount,
            'loseFinal':self.isWinFinalOrFlow(),
            'winFinal':self.isWinFinalOrFlow()
        }
	#modify end
        # 补充winNode
        if winNode:
            customInfo['winNode'] = winNode
            
        # 十风或者十三幺时显示打出的牌
        dropTiles = self.tableTileMgr.dropTiles[seatId]
        if NeedDropTiles:
            customInfo['dropTiles'] = dropTiles



        scores = {}
        scores['totalScore'] = self.tableResult.score
        if self.tableConfig.get(MTDefine.OVER_BY_SCORE, 0):
            # 总积分是玩家积分 不是输赢积分
            scores['totalScore'] = currentScore

        scores['deltaScore'] = self.roundResult.score
        scores['deltaGangScore'] = self.roundResult.getRoundGangResult()
        scores['deltaWinScore'] = self.roundResult.getRoundWinResult()

        self.setLastWins(wins)
        self.setLastLooses(looses)
        if not len(wins) > 1:
            if not (cp.xuezhanRank == -1):
                cp.setXuezhanRank(self.getWinPlayerCount())
        self.msgProcessor.table_call_game_win_loose(uids
                , wins
                , looses
                , observers
                , winMode
                , tile
                , scores
                , scoreBase
                , fanPattern
                , customInfo
                , piaoPoints
                ,flowerScores
                , displayExtends
		,lastSeatId
                ,self.isWinFinalOrFlow())
        # 处理胡牌，判断游戏是否结束，没结束继续游戏
   	ftlog.debug('table_logic score:',self.roundResult.score)
        # 一炮多响
        if len(wins) > 1:
	    self.processHu(self.players[len(wins)-1])
        else:
	    self.processHu(cp)

    def calcBestWinner(self,wins = [],isGangKai = False):
        tempMode = 0
        winInfos = []        
        for winSeatId in wins:
            winMode = self.players[winSeatId].winMode
            if winMode > tempMode:
                tempMode = winMode
                if tempMode >=5 and tempMode != 7:
                    playWinInfo = []
                    playWinInfo.append(winSeatId)
                    playWinInfo.append(winMode)
                    winInfos.append(playWinInfo)
        
        bestMode = 10
        bestWinner = None
        for winInfo in winInfos:
            if winInfo[1] < bestMode:
                bestMode = winInfo[1]
                bestWinner = winInfo[0]
	ftlog.debug('MajiangTableLogic.calcBestWinner bestWinner=',bestWinner,bestMode)
        ### 金雀的winMode = 8
        if bestWinner != None:
            return True,[bestWinner]
        else:
            curSeat = self.curSeat
            for index in range(self.playerCount):
                seatId = (curSeat + index) % self.playerCount
                if seatId in wins:
                    bestWinner = seatId
                    break
                else:
                    curSeat = seatId
	    return True,[bestWinner]

    def gameFlow(self, seatId):
        """流局,所有人都是lose,gameflow字段为1"""
        ftlog.debug( 'MajiangTableLogic.gameFlow seatId:',seatId)
        
        # 结算的类型
        # 1 吃和
        # 0 自摸
        # -1 输牌
        tile = 0
        wins = []
        looses = []
        observers = []
	gameflow = True
        #cp = self.__players[seatId]
        # 流局所有人都是loose
        for player in self.players:
            if self.checkTableState(MTableState.TABLE_STATE_XUEZHAN) or self.checkTableState(MTableState.TABLE_STATE_XUELIU):
                if player.isWon():
                    wins.append(player.curSeatId)
		    gameFlow = False
		else:
		    looses.append(player.curSeatId)
            else:
	        looses.append(player.curSeatId)
        ftlog.debug('MajiangTableLogic.gameFlow players:',len(wins),len(looses))
        if self.addCardProcessor.getState() != 0:
            exInfo = self.addCardProcessor.extendInfo
            if exInfo:
                ftlog.debug('gameFlow exInfo:', exInfo)
        elif self.__drop_card_processor.getState() != 0:
            self.__drop_card_processor.updateProcessor(self.actionID, seatId, MTableState.TABLE_STATE_HU, tile, None)
            self.__drop_card_processor.reset()
                    
        # 记录杠牌得分
        winBase = self.getTableConfig(MTDefine.WIN_BASE, 1)
        ftlog.debug('MajiangTableLogic.gameFlow winBase: ', winBase)
        
        winMode = [MOneResult.WIN_MODE_LOSS for _ in range(len(self.__players))]
        fanPattern = [[] for _ in range(len(self.__players))]
        currentScore = [0 for _ in range(self.playerCount)]
        piaoPoints = None
        flowerScores = None
        displayExtends = None
        moziScores = None
        lianzhuangCount = None
	if winBase > 0:
            result = MOneResultFactory.getOneResult(self.playMode)
            result.setResultType(MOneResult.RESULT_FLOW)
            result.setLastSeatId(seatId)
            result.setWinSeatId(-1)
            result.setTableConfig(self.tableConfig)
            result.setBankerSeatId(self.queryBanker())
            result.setPlayerCount(self.playerCount)
            tingState = [0 for _ in range(self.playerCount)]
            colorState = [0 for _ in range(self.playerCount)]
            menState = [0 for _ in range(self.playerCount)]
            ziState = [[0,0,0,0,0,0,0] for _ in range(self.playerCount)]
            playerAllTiles = [0 for _ in range(self.playerCount)]

            for player in self.player:
                playerAllTiles[player.curSeatId] = player.copyTiles()
                # 听牌状态
                if player.isTing():
                    tingState[player.curSeatId] = 1
                # 花色状态    
                pTiles = player.copyTiles()
                tileArr = MTile.changeTilesToValueArr(MHand.copyAllTilesToList(pTiles))
                colorState[player.curSeatId] = MTile.getColorCount(tileArr)
                tempTiles = MTile.traverseTile(MTile.TILE_FENG)
                ziState[player.curSeatId] = tileArr[tempTiles[0]:tempTiles[len(tempTiles)-1]+1]
                # 门清状态
                handTiles = player.copyHandTiles()
                gangTiles = player.copyGangArray()
                ming,an = MTile.calcGangCount(gangTiles)
                if len(handTiles) == self.handCardCount-an*3:
                    menState[player.curSeatId] = 1
                    
            result.setMenState(menState)
            result.setTingState(tingState)
            result.setDoublePoints(self.doubleProcessor.doublePoints)
            result.setColorState(colorState)
            result.setZiState(ziState)
            result.setPlayerAllTiles(playerAllTiles)
            result.setWinTile(-1)
            result.setTableTileMgr(self.tableTileMgr)
            result.setWinRuleMgr(self.winRuleMgr)
            result.setMultiple(self.__win_rule_mgr.multiple)
            result.setPiaoProcessor(self.piaoProcessor)
            result.setActionID(self.actionID)
            result.calcScore(self.__gang_scores)
            self.setLatestGangState(-1)
            self.__win_rule_mgr.setLastGangSeat(-1)
	    ftlog.debug('MajiangTableLogic.gameFlow playMode=',self.playMode)
            self.roundResult.setPlayMode(self.playMode)
            self.roundResult.addRoundResult(result)
            #加上牌桌上局数总分
            tableScore = [0 for _ in range(self.playerCount)]
            if self.tableResult.score:
                tableScore = self.tableResult.score
	    for i in range(self.playerCount):
                currentScore[i] = tableScore[i] + self.roundResult.score[i]
                if self.tableConfig.get(MTDefine.OVER_BY_SCORE, 0):
                    curBaseCount = self.tableConfig[MFTDefine.CUR_BASE_COUNT]
                    currentScore[i] = self.player[i].getCurScoreByBaseCount(curBaseCount)

            self.msgProcessor.table_call_score(self.getBroadCastUIDs(), currentScore, self.roundResult.delta)
            if MOneResult.KEY_WIN_MODE in result.results:
                winMode = result.results[MOneResult.KEY_WIN_MODE]

            #计算手牌杠
            self.calcGangInHand(-1,seatId, tile, playerAllTiles,result.winNodes)

            if MPlayMode().isSubPlayMode(self.playMode, MPlayMode.LUOSIHU):
                fanPattern = self.roundResult.getMergeFanPatternList()
            else:
                if MOneResult.KEY_FAN_PATTERN in result.results:
                    fanPattern = result.results[MOneResult.KEY_FAN_PATTERN]
                #带上明杠暗杠oneResult中的番型信息
                fanPattern = self.appendGangFanPattern(fanPattern)

            if MOneResult.KEY_DISPLAY_EXTEND in result.results:
                displayExtends = result.results[MOneResult.KEY_DISPLAY_EXTEND]

            if MOneResult.KEY_MOZI in result.results:
                moziScores = result.results[MOneResult.KEY_MOZI]

            if MOneResult.KEY_LIANZHUANG in result.results:
                lianzhuangCount = result.results[MOneResult.KEY_LIANZHUANG]

        # 处理流局
        scoreBase = self.getTableConfig(MTDefine.SCORE_BASE, 0)
	self.__table_result.addResult(self.roundResult)
        uids = self.getBroadCastUIDs()
        
        # 更新圈数        
        self.calcQuan(self.__playerCount, 0, seatId)
        
        # 流局，局数不加1
        ctInfo = self.getCreateTableInfo()
        btInfo, _ = self.getBaoPaiInfo()
        # 获取最后的特殊牌协议
        lstInfo = self.tableTileMgr.getLastSpecialTiles(self.bankerMgr.queryBanker())
        customInfo = {
            'ctInfo':ctInfo,
            'btInfo':btInfo,
            'lstInfo':lstInfo,
            'moziScores':moziScores,
            'lianzhuangCount':lianzhuangCount,
	    'winFinal': 1,
            'loseFinal': 1,
            'gameFlow': gameflow
            }

        scores = {}
        scores['totalScore'] = self.tableResult.score
        scores['deltaScore'] = self.roundResult.score
        scores['deltaGangScore'] = self.roundResult.getRoundGangResult()
        scores['deltaWinScore'] = self.roundResult.getRoundWinResult()

        if self.tableConfig.get(MTDefine.OVER_BY_SCORE, 0):
            # 总积分是玩家积分 不是输赢积分
            scores['totalScore'] = currentScore
        self.msgProcessor.table_call_game_win_loose(uids
                , wins
                , looses
                , observers
                , winMode
                , -1
                , scores
                , scoreBase
                , fanPattern
                , customInfo
                , piaoPoints
                , flowerScores
                , displayExtends
		,self.curSeat
                ,self.isWinFinalOrFlow())
        # 处理流局，判断游戏是否结束
        self.processFlow()
                
    def getWinPlayerCount(self):
        count = 0
        for player in self.__players:
            if player.state == MPlayer.PLAYER_STATE_WON:
                count += 1
        return count

    def isWinFinalOrFlow(self):
	winFinal = True
        if self.checkTableState(MTableState.TABLE_STATE_XUEZHAN):
            if self.getWinPlayerCount() >= self.playerCount - 1 :
                winFinal = True
            else:
		winFinal = False
        if self.checkTableState(MTableState.TABLE_STATE_XUELIU):
            if self.haveRestTile():
		winFinal = False
            else:
		winFinal = True

	return winFinal
                
    def processHu(self, player,grabHuGang = False):     
        # 根据玩法需要是继续还是游戏结束
	# grabHuGang 是否抢杠胡，用于血战，血流modify  by yj 05.06
        ftlog.debug( 'MajiangTableLogic.processHu...' )
        if self.checkTableState(MTableState.TABLE_STATE_XUEZHAN):
            # 有三个人和了，游戏结束
            if self.getWinPlayerCount() >= self.playerCount - 1:
                self.resetGame(1)
                return True
            else:
		if not grabHuGang:
                    self.__cur_seat = player.curSeatId
        elif self.checkTableState(MTableState.TABLE_STATE_XUELIU):
	    if self.playMode != 'luosihu-luosihu':
	        if not grabHuGang:
		    self.__cur_seat = player.curSeatId
        else:
            ftlog.debug( 'MajiangTableLogic.processHu normal gameover...' )
            self.resetGame(1)
            return True
        
        return False
    
    def processFlow(self):
        # 流局游戏结束
        ftlog.debug( 'MajiangTableLogic.processFlow...' )
	if self.playMode == 'luosihu-ctxuezhan':
	    if self.getWinPlayerCount() > 0:
		self.resetGame(1)
		return True
        self.resetGame(0)
        return True
    
    def playerCancel(self, seatId):
        """用户选择放弃
        """
        cancelPlayer = self.player[seatId]
        tile = 0
        if self.__drop_card_processor.getState() != 0:
            ftlog.debug("playerCancel Drop", seatId)
            tile = self.__drop_card_processor.getTile()

            # 别人出牌检查过胡
            # pass后将漏胡的牌加入过胡牌数组,下次轮到自己回合时清空
            # 遍历所有牌，检测玩家所有可以胡的牌，全部加到列表
            if self.__win_rule_mgr.isPassHu() and  self.__drop_card_processor.getStateBySeatId(seatId) & MTableState.TABLE_STATE_HU:
                self.tableTileMgr.addPassHuBySeatId(seatId, tile)

            playerProcessor = self.__drop_card_processor.processors[seatId]
            self.__drop_card_processor.resetSeatId(seatId)
            dropState = self.__drop_card_processor.getState()
            ftlog.debug('playerCancel dropState:', dropState)

            if playerProcessor['state'] & MTableState.TABLE_STATE_PENG:  # 过碰
                pengs = playerProcessor['extendInfo'].getChiPengGangResult(MTableState.TABLE_STATE_PENG)
                if pengs:
                    for peng in pengs:
                        cancelPlayer.guoPengTiles.add(peng[0])
            if playerProcessor['state'] & MTableState.TABLE_STATE_HU:  # 过胡
                cancelPlayer.guoHuPoint = cancelPlayer.totalWinPoint
                ftlog.debug('playerCancel cancelPlayer.guoHuPoint:', cancelPlayer.guoHuPoint)
        if self.addCardProcessor.getState() != 0:
            ftlog.debug("playerCancel Add", seatId)
            tile = copy.deepcopy(self.addCardProcessor.getTile())
            addState = copy.deepcopy(self.addCardProcessor.state)
            #成功取消才继续
            if self.addCardProcessor.updateProcessor(self.actionID, 0, seatId):
                ftlog.debug('MajiangTableLogic.playerCancel tile:', tile, ' addState:', addState)
                if cancelPlayer.isTing() and addState & MTableState.TABLE_STATE_HU:
                    ftlog.debug('MajiangTableLogic.playerCancel, user pass win, drop tile directly....')
                    self.dropTile(seatId, tile)

            if addState & MTableState.TABLE_STATE_HU or addState & MTableState.TABLE_STATE_GANG:
                noDropCardCount = self.tableTileMgr.getTilesNoDropCount()
                if self.tableTileMgr.getCheckFlowCount() < noDropCardCount:
		    self.msgProcessor.table_call_last_round_broadcast(self.getBroadCastUIDs())
                    # 剩余四张牌 玩家摸牌有杠和胡 点开过的处理
                    nextSeat = self.nextSeatId(self.__cur_seat)
                    self.__cur_seat = nextSeat
                    self.processAddTile(self.player[nextSeat], MTableState.TABLE_STATE_NEXT)

            if addState & MTableState.TABLE_STATE_HU:
                cancelPlayer.guoHuPoint = cancelPlayer.totalWinPoint  # 过胡

        if self.__qiang_gang_hu_processor.getState() != 0:
            ftlog.debug("playerCancel QiangGangHu", seatId)
            tile = self.__qiang_gang_hu_processor.tile
            self.__qiang_gang_hu_processor.resetSeatId(seatId)
            if self.__qiang_gang_hu_processor.getState() == 0:
                ftlog.debug( '__qiang_gang_hu_processor all player check')
                #恢复挂起的杠牌状态 允许原来杠牌的玩家继续杠牌
                gangSeatId = self.__qiang_gang_hu_processor.curSeatId
                gangState = self.__qiang_gang_hu_processor.gangState
                gangSpecialTile = self.__qiang_gang_hu_processor.specialTile
                gangTile = self.__qiang_gang_hu_processor.tile
                gangPattern = self.__qiang_gang_hu_processor.gangPattern
                gangStyle = self.__qiang_gang_hu_processor.style
                self.justGangTile(self.curSeat, gangSeatId, gangTile, gangPattern, gangStyle, gangState, True, gangSpecialTile, self.__qiang_gang_hu_processor.qiangGangSeats)
		ftlog.debug('__qiang_gang_hu_processor.qiangGangSeats = ', self.__qiang_gang_hu_processor.qiangGangSeats)
                self.__qiang_gang_hu_processor.clearQiangGangSeats()
            if self.curState() == 0:
                self.__cur_seat = (self.__cur_seat - 1) % self.playerCount
            # 过胡
            cancelPlayer.guoHuPoint = cancelPlayer.totalWinPoint

        if self.qiangExmaoPengProcessor.getState() != 0:
            ftlog.debug("playerCancel Qiangmaopeng", seatId)

            tile = self.qiangExmaoPengProcessor.tile
            self.qiangExmaoPengProcessor.resetSeatId(seatId)
            if self.qiangExmaoPengProcessor.getState() == 0:
                ftlog.debug( 'qiangExmaoPengProcessor all player check')
                #恢复挂起的exmao状态 允许原来exmao的玩家继续exmao
                maoSeatId = self.qiangExmaoPengProcessor.curSeatId
                maoTile = self.qiangExmaoPengProcessor.tile
                maoStyle = self.qiangExmaoPengProcessor.style
                self.justExmao(maoSeatId, maoTile, maoStyle)
                
                self.qiangExmaoPengProcessor.reset()
            if self.curState() == 0:
                self.__cur_seat = (self.__cur_seat - 1) % self.playerCount
                
        if self.qiangExmaoHuProcessor.getState() != 0:
            ftlog.debug("playerCancel qiangExmaoHuProcessor", seatId)

            tile = self.qiangExmaoHuProcessor.tile
            self.qiangExmaoHuProcessor.resetSeatId(seatId)
            if self.qiangExmaoHuProcessor.getState() == 0:
                ftlog.debug( 'qiangExmaoHuProcessor all player check')
                #恢复挂起的exmao状态 允许原来exmao的玩家继续exmao
                maoSeatId = self.qiangExmaoHuProcessor.curSeatId
                maoTile = self.qiangExmaoHuProcessor.tile
                maoStyle = self.qiangExmaoHuProcessor.style
                self.justExmao(maoSeatId, maoTile, maoStyle)
                
                self.qiangExmaoHuProcessor.reset()
            if self.curState() == 0:
                self.__cur_seat = (self.__cur_seat - 1) % self.playerCount
                
                
        if self.tingBeforeAddCardProcessor.getState() != 0:
            ftlog.debug('playerCancel minglou...')
            if self.tingBeforeAddCardProcessor.updateProcessor(self.actionID, MTableState.TABLE_STATE_NEXT, seatId):
                self.tingBeforeAddCardProcessor.reset()
                self.processAddTile(self.player[seatId], MTableState.TABLE_STATE_NEXT)

        if self.tianTingProcessor.getState() != 0:
            ftlog.debug('playerCancel tianting...')
            if self.tianTingProcessor.updateProcessor(seatId):
                if self.tianTingProcessor.getState() == 0:
                    #self.msgProcessor.setTianTing(False)
                    for player in self.player:
                        if player.curSeatId == self.queryBanker():
                            self.msgProcessor.table_call_tian_ting_over(player.curSeatId, self.actionID)

        if self.louHuProcesssor.getState() != 0:
            ftlog.debug('playerCancel louhu...')
            if self.louHuProcesssor.updateProcessor(self.actionID, MTableState.TABLE_STATE_NEXT, seatId):
                self.louHuProcesssor.reset()

    def appendGangFanPattern(self, fanPattern):
        for ri in range(0, len(self.roundResult.roundResults) - 1)[::-1]:
            if self.roundResult.roundResults[ri].results[MOneResult.KEY_TYPE] == MOneResult.KEY_TYPE_NAME_HU:
                #倒序统计杠牌信息
                break
            else:
                #本局的杠牌记录
                if MOneResult.KEY_STAT in self.roundResult.roundResults[ri].results:
                    roundStat = self.roundResult.roundResults[ri].results[MOneResult.KEY_STAT]
                    for rsi in range(len(roundStat)):
                        for statItems in roundStat[rsi]:
                            for oneStatItemKey in statItems.keys():
                                if oneStatItemKey == MOneResult.STAT_MINGGANG:
                                    mingGangName = self.roundResult.roundResults[ri].statType[MOneResult.STAT_MINGGANG]["name"]
                                    mingGangFanPattern = [mingGangName, str(1)+"番"]
                                    if mingGangFanPattern not in fanPattern[rsi]:
                                        fanPattern[rsi].append(mingGangFanPattern)
                                        
                                if oneStatItemKey == MOneResult.STAT_ANGANG:
                                    anGangName = self.roundResult.roundResults[ri].statType[MOneResult.STAT_ANGANG]["name"]
                                    anGangFanPattern = [anGangName, str(1)+"番"]
                                    if anGangFanPattern not in fanPattern[rsi]:
                                        fanPattern[rsi].append(anGangFanPattern)

                                if oneStatItemKey == MOneResult.STAT_BaoZhongGANG:
                                    ftlog.info("appendGangFanPattern STAT_BaoZhongGANG:")
                                    GangName = self.roundResult.roundResults[ri].statType[MOneResult.STAT_BaoZhongGANG]["name"]
                                    GangFanPattern = [GangName, str(1)+"番"]
                                    if GangFanPattern not in fanPattern[rsi]:
                                        fanPattern[rsi].append(GangFanPattern)
        return fanPattern
        
    def printTableTiles(self):
        """打印牌桌的所有手牌信息"""
        for player in self.player:
            player.printTiles()
        self.tableTileMgr.printTiles()
            
    def refixTableStateByConfig(self):
        """根据自建房配置调整牌桌状态"""
        chipengSetting = self.tableConfig.get(MTDefine.CHIPENG_SETTING, 0)
        ftlog.info("refixTableStateByConfig chipengSetting:", chipengSetting)
        if chipengSetting == MTDefine.NOT_ALLOW_CHI:
            if self.checkTableState(self.__table_stater.TABLE_STATE_CHI):
                self.__table_stater.clearState(self.__table_stater.TABLE_STATE_CHI)
                ftlog.debug("refixTableStateByConfig remove TABLE_STATE_CHI, now chi state =", self.checkTableState(self.__table_stater.TABLE_STATE_CHI))
        elif chipengSetting == MTDefine.ALLOW_CHI:
            if not self.checkTableState(self.__table_stater.TABLE_STATE_CHI):
                self.__table_stater.setState(self.__table_stater.TABLE_STATE_CHI)
                ftlog.debug("refixTableStateByConfig add TABLE_STATE_CHI, now chi state =", self.checkTableState(self.__table_stater.TABLE_STATE_CHI))


        gangSetting = self.tableConfig.get(MTDefine.GANG_SETTING, 0)
        ftlog.info("refixTableStateByConfig gangSetting:", gangSetting)
        if gangSetting == 1:#can not gang
            if self.checkTableState(self.__table_stater.TABLE_STATE_GANG):
                self.__table_stater.clearState(self.__table_stater.TABLE_STATE_GANG)
                ftlog.info("refixTableStateByConfig gangSetting:gangSetting == 1:#can not gang")
        elif gangSetting == 2:#can gang
            if not self.checkTableState(self.__table_stater.TABLE_STATE_GANG):
                self.__table_stater.setState(self.__table_stater.TABLE_STATE_GANG)
                ftlog.info("refixTableStateByConfig gangSetting:gangSetting == 2:#can gang")
        ftlog.info("refixTableStateByConfig ",self.checkTableState(self.__table_stater.TABLE_STATE_GANG))


        tingSetting = self.tableConfig.get(MTDefine.TING_SETTING, MTDefine.TING_UNDEFINE)
        ftlog.debug('refixTableStateByConfig tingSetting:', tingSetting)
        if tingSetting == MTDefine.TING_YES:
            if not self.checkTableState(MTableState.TABLE_STATE_TING):
                self.tableStater.setState(MTableState.TABLE_STATE_TING)
                self.__ting_rule_mgr = MTingRuleFactory.getTingRule(self.playMode)
                self.__ting_rule_mgr.setWinRuleMgr(self.__win_rule_mgr)
                self.__ting_rule_mgr.setTableTileMgr(self.tableTileMgr)
                ftlog.debug('refixTableStateByConfig add TABLE_STATE_TING...')
        elif tingSetting == MTDefine.TING_NO:
            if self.checkTableState(MTableState.TABLE_STATE_TING):
                self.tableStater.clearState(MTableState.TABLE_STATE_TING)
                ftlog.debug('refixTableStateByConfig clear TABLE_STATE_TING...')

        piaoSetting = self.tableConfig.get(MTDefine.PIAO_SETTING, MTDefine.PIAO_UNDEFINE)
        ftlog.debug('refixTableStateByConfig piaoSetting:', piaoSetting)
        if piaoSetting == MTDefine.PIAO_YES:
            if not self.checkTableState(MTableState.TABLE_STATE_PIAO):
                self.tableStater.setState(MTableState.TABLE_STATE_PIAO)
                ftlog.debug('refixTableStateByConfig add TABLE_STATE_PIAO...')
        elif piaoSetting == MTDefine.PIAO_NO:
            if self.checkTableState(MTableState.TABLE_STATE_PIAO):
                self.tableStater.clearState(MTableState.TABLE_STATE_PIAO)
                ftlog.debug('refixTableStateByConfig clear TABLE_STATE_PIAO...')

        doubleSetting = self.tableConfig.get(MTDefine.DOUBLE_SETTING, MTDefine.DOUBLE_UNDEFINE)
        ftlog.debug('refixTableStateByConfig doubleSetting:', doubleSetting)
        if doubleSetting == MTDefine.DOUBLE_YES:
            if not self.checkTableState(MTableState.TABLE_STATE_DOUBLE):
                self.tableStater.setState(MTableState.TABLE_STATE_DOUBLE)
                ftlog.debug('refixTableStateByConfig add TABLE_STATE_DOUBLE...')
        elif doubleSetting == MTDefine.DOUBLE_NO:
            if self.checkTableState(MTableState.TABLE_STATE_DOUBLE):
                self.tableStater.clearState(MTableState.TABLE_STATE_DOUBLE)
                ftlog.debug('refixTableStateByConfig clear TABLE_STATE_DOUBLE...')

        ftlog.debug('refixTableStateByConfig tableState:', self.tableStater.states)

    def refixTableMultipleByConfig(self):
        """根据传入配置调整输赢倍数"""
        multiple = self.tableConfig.get(MTDefine.MULTIPLE, MTDefine.MULTIPLE_MIN)
        ftlog.info('refixTableMutipleByConfig multiple:', multiple)
        if multiple >= MTDefine.MULTIPLE_MIN and multiple <= MTDefine.MULTIPLE_MAX:
            self.__win_rule_mgr.setMultiple(multiple)

        # 调整胡牌方式
        winType = self.tableConfig.get(MTDefine.WIN_SETTING, 0)
        ftlog.info('refixTableMutipleByConfig winType:', winType)
        if winType:
            self.__win_rule_mgr.setWinType(winType)

    def getShareFangkaConfig(self):
        """获取房卡支付配置"""
        ftlog.info('getShareFangkaConfig info:', self.tableConfig)
        share_fangka = self.tableConfig.get(MTDefine.SHARE_FANGKA,0)
        ftlog.info('getShareFangkaConfig info:', share_fangka)
        return share_fangka

    def checkItemCount(self, userId, itemId, gameId, roomId, bigRoomId,payMode = 0):
        ftlog.info("MajiangFriendTable.checkItemCount userId:", userId
                    , "itemId:", itemId
                    , "roomId:", roomId
                    , "bigRoomId", bigRoomId)
        user_fangka_count = MajiangItem.getUserItemCountByKindId(userId, itemId)
        ftlog.info('MajiangFriendTable.checkItemCount fangka used:',user_fangka_count, self.tableConfig[MFTDefine.CARD_COUNT],self.playerCount)

        # 大赢家支付房卡
        consume_fangka_count = 0
        if payMode == 1 :
            consume_fangka_count = self.tableConfig[MFTDefine.CARD_COUNT]
        if payMode == 2 :
            consume_fangka_count = self.tableConfig[MFTDefine.CARD_COUNT]/self.playerCount
        else:
            consume_fangka_count = self.tableConfig[MFTDefine.CARD_COUNT]
        ftlog.info('MajiangFriendTable.checkItemCount fangka cusume:',consume_fangka_count)
        if user_fangka_count >= consume_fangka_count:
            consumeResult = user_remote.consumeItem(userId, gameId, itemId, consume_fangka_count, roomId, bigRoomId)
            if not consumeResult:
                return False
            return True
        return False

    def playerLeave(self,seatId):
        player = self.getPlayer(seatId)
        if not player:
            return
        
        player.setOffline()
        
    def playerEnterBackGround(self, seatId):
        self.player[seatId].setBackForeState(MPlayer.BACK_GROUND)
        
    def playerResumeForeGround(self, seatId):
        self.player[seatId].setBackForeState(MPlayer.FORE_GROUND)
        
    def playerOnline(self,seatId):
        player = self.getPlayer(seatId)
        player.setOnline()
        player.setBackForeState(MPlayer.FORE_GROUND)

    def sendPlayerLeaveMsg(self, userId):
        userIds = self.getBroadCastUIDs(userId)
        online_info_list = []
        for player in self.player:
            if not player:
                continue
            
            online_info = {}
            online_info['userId'] = player.userId
            online_info['seatId'] = player.curSeatId
            online_info['online'] = player.curOnlineState
            online_info['state'] = player.backForeState
            online_info_list.append(online_info)
            ftlog.info('leave players info:', online_info)

        self.msgProcessor.table_call_player_leave(userIds, online_info_list)

    def sendUserNetState(self, userId, seatId, ping, time):
        ftlog.debug('userNetState:',userId, ping)
        self.__players_ping[userId] = ping
        ping_info = [0 for _ in range(self.playerCount)]
        seats = [0 for _ in range(self.playerCount)]
        for index,_ in enumerate(seats):
            if self.__players[index]:
                if self.__players_ping.has_key(self.__players[index].userId) != True:
                    self.__players_ping[self.__players[index].userId] = 0
                ping_info[index] = self.__players_ping[self.__players[index].userId]
        self.msgProcessor.table_call_ping(userId, ping_info, time)

    def isStart(self):
        if self.__table_win_state != MTableState.TABLE_STATE_NONE and self.__table_win_state != MTableState.TABLE_STATE_GAME_OVER:
            return True
        return False

    def buFlower(self, seatId, tile):
        """补花，怀宁麻将需要人工请求补花"""
        if not self.flowerRuleMgr.isFlower(tile):
            return

        cp = self.player[seatId]
        if tile not in cp.handTiles:
            return

        # 执行补花
        cp.handTiles.remove(tile)
        cp.flowers.append(tile)
        self.msgProcessor.table_call_bu_flower_broadcast(seatId, tile, cp.flowers,self.tableTileMgr.flowerScores(seatId), self.getBroadCastUIDs())

        state = MTableState.TABLE_STATE_NEXT
        if self.tableConfig.get(MFTDefine.BU_FLOWER_AS_GANG, 0):
            state |= MTableState.TABLE_STATE_GANG
            cp.curLianGangNum += 1  # 连杠次数+1

        # 摸牌
        self.processAddTile(cp, state)

    def autoBuFlower(self):
        """自动补花"""
        isBeginGame = self.flowerProcessor.isBegin
        nextSeatId = self.flowerProcessor.seatId
        flowers, seatId = self.flowerProcessor.getFlower(self.curSeat)
        flower_action = [[] for _ in range(len(flowers)) ]
        tiles = [0 for _ in range(len(flowers))]
        if len(flowers) > 0 and isBeginGame:
            cp = self.player[seatId]
            ftlog.debug('autoBuFlower xxx 1',cp.handTiles,flowers)
	    # 执行补花
	    
            for index in range(len(flowers)):
                if self.haveRestTile():    
                    cp.handTiles.remove(flowers[index])
                    cp.flowers.append(flowers[index])
                    self.tableTileMgr.setFlowerTileInfo(flowers[index],seatId)
                    cp.addFlowerScores(1)
                    self.tableTileMgr.addFlowerScores(1, seatId)

                    oneTile = self.popOneTile(cp.curSeatId)
                    cp.actionAdd(oneTile)
		    tiles[index] = oneTile
                    #self.incrActionId('addTileSimple')
                else:
                    self.gameFlow(cp.curSeatId)
                    return
	    
	    for index in range(len(flowers)):
                flower_action[index].append(flowers[index])
		flower_action[index].append(0)
		ftlog.debug('autoBuFlower xxx 2',index,flower_action,flowers) 
	    for player in self.players:
		isSelf = False
		if cp.curSeatId == player.curSeatId:
		    isSelf = True
		    for index in range(len(flowers)):
			flower_action[index][1] = tiles[index]
		else:
                    for index in range(len(flowers)):
                        flower_action[index][1] = 0
                self.msgProcessor.table_call_first_bu_flower_broadcast(seatId, flower_action, cp.flowers, self.tableTileMgr.flowerScores(seatId), player.userId,self.__flower_round,isSelf)
        elif len(flowers) > 0 and not isBeginGame:
            flower = flowers[0]
            if flower and self.flowerRuleMgr.isFlower(flower):
                cp = self.player[seatId]
                # 执行补花
                cp.handTiles.remove(flower)
                cp.flowers.append(flower)
                self.tableTileMgr.setFlowerTileInfo(flower,seatId)

                # 累计花分
                cp.addFlowerScores(1)
                self.tableTileMgr.addFlowerScores(1, seatId)
                self.msgProcessor.table_call_bu_flower_broadcast(seatId, flower, cp.flowers, self.tableTileMgr.flowerScores(seatId), self.getBroadCastUIDs())

                self.processAddTile(self.player[seatId], MTableState.TABLE_STATE_NEXT, None, {"buFlower": 1})
                ftlog.debug('MajiangTableLogic.bu_flower flower:', flower
                            , ' seatId:', seatId
                            , ' handTiles:', cp.handTiles
                            , ' flowers:', cp.flowers)
	


        #开局全体补花
        if self.checkTableState(MTableState.TABLE_STATE_BUFLOWER):
            flowers = self.flowerRuleMgr.getAllFlowers(self.player)
            flowerCount = self.flowerRuleMgr.getFlowerCount(flowers)
            self.flowerProcessor.setMsgProcessor(self.msgProcessor)
            if flowerCount > 0 and self.flowerProcessor.getState() == MTableState.TABLE_STATE_NEXT and isBeginGame:
                self.flowerProcessor.initProcessor(MTableState.TABLE_STATE_BUFLOWER, flowers, True, self.curSeat)
		self.__flower_round = self.__flower_round + 1
                return

        #开局阶段的全体补花完毕
        if self.flowerProcessor.getState() == MTableState.TABLE_STATE_NEXT and isBeginGame:
	    self.msgProcessor.table_call_player_buFlower_end(self.getBroadCastUIDs())
	    if self.checkTableState(MTableState.TABLE_STATE_KAIJIN):
		self.kaijinProcessor.initProcessor(MTableState.TABLE_STATE_KAIJIN
                            , self.bankerMgr.queryBanker()
                            , self.msgProcessor
                            , self.getBroadCastUIDs())
                return True
	    if not MPlayMode().isSubPlayMode(self.playMode, MPlayMode.QUESHOU):	
                self.processAddTile(self.player[self.curSeat], MTableState.TABLE_STATE_NEXT)

        for player in self.players:
            ftlog.debug('MajiangTableLogic.autoBuFlower player seatId:',player.curSeatId,player.copyHandTiles())

    def autoKaijin(self):
        magicTile = self.kaijinProcessor.beginKaijin()
        if magicTile and self.kaijinProcessor.getState()== MTableState.TABLE_STATE_NEXT:
	    qiangjinResult,states,timeOut = self.checkBeginHu()
	    self.qiangjinProcessor.reset()
            if qiangjinResult:  
                self.qiangjinSchedule(states, self.actionID, timeOut)
		self.msgProcessor.table_call_lock_qiangjin(self.players[self.curSeat].userId)
	    else:
                curPlayer = self.players[self.curSeat]
                state = MTableState.TABLE_STATE_NEXT
                state, exInfo = self.calcAddTileExtendInfo(curPlayer, state, curPlayer.curTile, [])
		if state & MTableState.TABLE_STATE_GANG:
	   	    self.msgProcessor.table_call_ask_gang(curPlayer, curPlayer.curTile, self.actionID, exInfo)
	        self.__qiangjin = True

    def dingAbsence(self, userId, seatId, color):
        """定缺"""
        # 不处于定缺阶段不能定缺
        if self.absenceProcessor.getState() == 0:
            return

        self.absenceProcessor.dingAbsence(seatId, color)

        # 现在不处于定缺阶段，表明所有人都已定完缺
        if self.absenceProcessor.getState() == 0:
            self.winRuleMgr.setAbsenceColor(self.absenceProcessor.absenceColor)
            absenceInfo = []
	    for seatId in xrange(self.playerCount):
                cp = self.players[seatId]
		absenceInfo.append([cp.userId,self.absenceProcessor.absenceColor[cp.curSeatId]])
                #self.msgProcessor.table_call_absence_end(cp.userId, seatId, self.absenceProcessor.absenceColor)
	    for seatId in xrange(self.playerCount):
		cp = self.players[seatId]
		cp.setAbsenceColor(self.absenceProcessor.absenceColor[cp.curSeatId])
	    	self.msgProcessor.table_call_absence_end(cp.userId, cp.curSeatId, absenceInfo)
	    # 处理后续逻辑
            self.handleAbsenceEnd()

    def handleAbsenceEnd(self):
        """定缺结束处理
        """
        # 对闲家判天听, 跟无为的发牌时判断闲家天听一样
        if self.checkTableState(MTableState.TABLE_STATE_TING):
            self.tableStater.setState(MTableState.TABLE_STATE_TING)
            # 不需要处理庄家
            isTianTing = 0
            for cp in self.player:
                # 测试当前玩家是否可以听
                canTing, winNodes = self.tingRule.canTingBeforeAddTile(cp.copyTiles()
                                                                       , self.tableTileMgr.tiles
                                                                       ,self.tableTileMgr.getMagicTiles(cp.isTing())
                                                                       , self.__cur_seat
                                                                       , cp.curSeatId
                                                                       , self.actionID)
                ftlog.debug('MajiangTableLogic.handleAbsenceEnd, tian, canTing:', canTing
                            , ' winNodes:', winNodes)
                if canTing:
                    isTianTing = 1
                    self.tianTingProcessor.initProcessor(MTableState.TABLE_STATE_TING, cp.curSeatId, winNodes, 9)
                    winTiles = self.tianTingProcessor.getWinTiles(cp.curSeatId)
                    ftlog.debug('MajiangTableLogic.handleAbsenceEnd tianTingProcessor winTiles:', winTiles)
                    if self.queryBanker() != cp.curSeatId:
                        self.msgProcessor.table_call_ask_ting(cp.curSeatId, self.actionID, winTiles, [], 9)
            if isTianTing:
                self.msgProcessor.setTianTing(True)

        # 对庄家，再走一次摸牌处理, 避免重写很多代码
        #banker = self.players[self.queryBanker()]
        #banker.handTiles.remove(banker.curTile)
        #self.processAddTile(banker, MTableState.TABLE_STATE_NEXT, special_tile=banker.curTile)

        # 给庄家发一张牌，等待庄家出牌
        cp = self.player[self.__cur_seat]
        self.processAddTile(cp, MTableState.TABLE_STATE_NEXT)

    def actionQiangjin(self,userId,seatId,state):
        if self.qiangjinProcessor.getState()==0:
            return 
        qiangjinResult,maxSeatId,maxState = self.qiangjinProcessor.setQiangjinState(seatId,state)
        if qiangjinResult:
	    self.__qiangjin = True
	    self.msgProcessor.table_call_unlock_qiangjin(self.players[self.curSeat].userId)
	    magicTile = self.tableTileMgr.getMagicTile()
	    if maxSeatId ==self.bankerMgr.queryBanker():
                if maxState == MTableState.TABLE_STATE_TIANHU:
                    self.gameWin(maxSeatId, self.players[maxSeatId].curTile,[],maxState)
                elif maxState == MTableState.TABLE_STATE_QIANGJIN_B:
		    player = self.players[maxSeatId]
		    tile = self.players[self.curSeat].curTile
                    isTing,tingArr = self.tingRule.canTingForQiangjin(player.copyTiles(), self.tableTileMgr.tiles, tile, self.tableTileMgr.getMagicTiles(player.isTing()),self.__cur_seat, player.curSeatId, self.actionID,True)
		    if isTing:
                        self.players[maxSeatId].actionDrop(tingArr[0]['dropTile'])
                        self.player[maxSeatId].actionAdd(magicTile)
                        self.gameWin(maxSeatId,magicTile,[],maxState)
		    #ftlog.debug('MajiangTableLogic.autoKaijin called isTing, tingArr=',isTing, tingArr)
		elif maxState == MTableState.TABLE_STATE_SANJINDAO:
		    self.gameWin(maxSeatId, self.players[self.curSeat].curTile,[],maxState,True)
            else:
		if maxState == MTableState.TABLE_STATE_QIANGJIN:
                    self.gameWin(maxSeatId, magicTile,[],maxState)
                elif maxState == MTableState.TABLE_STATE_SANJINDAO:
                    self.gameWin(maxSeatId, 0,[],maxState,True)
	    if not maxState:
                curPlayer = self.players[self.curSeat]
                state = MTableState.TABLE_STATE_NEXT
                state, exInfo = self.calcAddTileExtendInfo(curPlayer, state, curPlayer.curTile, [])
		if state & MTableState.TABLE_STATE_GANG:
	            self.msgProcessor.table_call_ask_gang(curPlayer, curPlayer.curTile, self.actionID, exInfo)
		

    def chooseChange3tiles(self, userId, seatId, tiles):
        """换三张"""
        # 不处于换三张阶段不能换三张
        if self.change3tilesProcessor.getState() == 0:
            return

        self.change3tilesProcessor.chooseChange3tiles(seatId, tiles)

        if self.change3tilesProcessor.getState() == 0:
            self.change3tilesEnd()
        

    def change3tilesEnd(self):
	#modify by youjun 04.27
        for seatId in range(self.playerCount):
            curPlayer = self.__players[seatId]
            # 发送发牌的消息
            self.__msg_processor.sendMsgInitTils(curPlayer.copyHandTiles()
                        , self.bankerMgr.queryBanker()
                        , curPlayer.userId, seatId,True)
        # 有定缺玩法的，设置进入定缺状态，庄家起手摸牌时不能打牌，且不显示胡牌
        if self.checkTableState(MTableState.TABLE_STATE_ABSENCE):
            self.absenceProcessor.reset()
            self.absenceSchedule()
        # 有定缺玩法的，此时庄稼摸完第一张牌，开始让玩家做定缺选择
        if self.checkTableState(MTableState.TABLE_STATE_ABSENCE):
            self.absenceProcessor.onBankerAddedFirstTile()
	    return
        else:
            # 给庄家发一张牌，等待庄家出牌
            cp = self.player[self.__cur_seat]
            self.processAddTile(cp, MTableState.TABLE_STATE_NEXT)
        # 对闲家判天听, 跟无为的发牌时判断闲家天听一样
        if self.checkTableState(MTableState.TABLE_STATE_TING):
            self.tableStater.setState(MTableState.TABLE_STATE_TING)
            # 不需要处理庄家
            isTianTing = 0
            for cp in self.player:
                # 测试当前玩家是否可以听
                canTing, winNodes = self.tingRule.canTingBeforeAddTile(cp.copyTiles()
                                                                       , self.tableTileMgr.tiles
                                                                       ,self.tableTileMgr.getMagicTiles(cp.isTing())
                                                                       , self.__cur_seat
                                                                       , cp.curSeatId
                                                                       , self.actionID)
                ftlog.debug('MajiangTableLogic.handleAbsenceEnd, tian, canTing:', canTing
                            , ' winNodes:', winNodes)
                if canTing:
                    isTianTing = 1
                    self.tianTingProcessor.initProcessor(MTableState.TABLE_STATE_TING, cp.curSeatId, winNodes, 9)
                    winTiles = self.tianTingProcessor.getWinTiles(cp.curSeatId)
                    ftlog.debug('MajiangTableLogic.handleAbsenceEnd tianTingProcessor winTiles:', winTiles)
                    if self.queryBanker() != cp.curSeatId:
                        self.msgProcessor.table_call_ask_ting(cp.curSeatId, self.actionID, winTiles, [], 9)
            if isTianTing:
                self.msgProcessor.setTianTing(True)

        return True

    def canTingBeforeAddTile(self, tiles, leftTiles, magicTiles = [], curSeatId = 0, winSeatId = 0, actionID = 0):
        """判断在摸牌之前是否可以听
        """
        ftlog.debug('MTile.changeTilesToValueArr', tiles[MHand.TYPE_HAND])
        leftTileArr = MTile.changeTilesToValueArr(leftTiles)
        leftTileCount = len(leftTileArr)
        ftlog.debug('MTing.canTing leftTiles:', leftTiles
                     , ' leftTileArr:', leftTileArr
                     , ' leftTileCount:', leftTileCount)
        
        result = []
        resultNode = self.canWinAddOneTile(leftTileArr, leftTileCount, tiles, magicTiles, curSeatId, winSeatId, actionID)
        if len(resultNode) > 0:
            winNode = {}
            winNode['winNodes'] = resultNode
            result.append(winNode)
                
        return len(result) > 0, result


    def canWinAddOneTile(self, leftTileArr, leftTileCount, tiles, magicTiles = [], curSeatId = 0, winSeatId = 0, actionID = 0):
        result = []
        for tile in range(leftTileCount):
            newTile = MTile.cloneTiles(tiles)
            newTile[MHand.TYPE_HAND].append(tile)
            # 测试停牌时，默认听牌状态
            winResult, winPattern,_ = self.__win_rule_mgr.isHu(newTile, tile, True, MWinRule.WIN_BY_MYSELF, magicTiles, [], curSeatId, winSeatId, actionID)
            if winResult:
                winNode = {}
                winNode['winTile'] = tile
                winNode['winTileCount'] = leftTileArr[tile]
                '''
		ftlog.debug('MTing.canWinAddOneTile winTile:', tile
                            , ' winTileCount:', winNode['winTileCount']
                            , ' winPattern:', winPattern)
                '''
		winNode['pattern'] = winPattern
                result.append(winNode)
        
        return result


if __name__ == "__main__":

    table = MajiangTableLogic(2, "luosihu", MRunMode.CONSOLE)
    table.setTableConfig({
        "win_base": 1,
        "gang_base": 0,
        "fan_rule": {
            "1": {"pihu": 1, "yadang": 2, "zimo": 3, "zimoyadang": 4, "minggang": 1, "angang": 2, "hunyise": 2,
                  "tongtian": 2, "sihe": 2, "duiduihu": 2, "gangkai": 2},
            "2": {"pihu": 1, "yadang": 2, "zimo": 3, "zimoyadang": 4, "minggang": 2, "angang": 4, "hunyise": 5,
                  "tongtian": 5, "sihe": 5, "duiduihu": 5, "gangkai": 5},
            "3": {"pihu": 2, "yadang": 4, "zimo": 6, "zimoyadang": 8, "minggang": 2, "angang": 4, "hunyise": 5,
                  "tongtian": 5, "sihe": 5, "duiduihu": 5, "gangkai": 5}
        },
        "jiaopai_rule": {
            "1": {"base_pay": 30, "zui_add": 10, "zimo_add": 15, "base_caps": 45},
            "2": {"base_pay": 50, "zui_add": 10, "zimo_add": 20, "base_caps": -1},
            "3": {"base_pay": 50, "zui_add": 10, "zimo_add": 20, "base_caps": -1}
        }
    })
    table.tableConfig[MFTDefine.BASE_COUNT] = 2
    table.tableConfig[MFTDefine.CUR_BASE_COUNT] = 2
    table.tableConfig[MFTDefine.INIT_SCORE] = 30

    table.refixTableStateByConfig()
    handler = ActionHandlerFactory.getActionHandler(MRunMode.CONSOLE)
    handler.setTable(table)

    # 姓名 性别 userId score 头像 金币
    player0 = MPlayer('0', 1, 10000, 0)
    table.addPlayer(player0, 0, True, False)
    table.sendMsgTableInfo(0)
    
    player1 = MPlayer('1', 1, 10001, 0)
    table.addPlayer(player1, 1, True, False)
    
    # player2 = MPlayer('2', 1, 10002, 0)
    # table.addPlayer(player2, 2, True, True)
    #
    # player3 = MPlayer('3', 1, 10003, 0)
    # table.addPlayer(player3, 3, True, True)
    table.sendMsgTableInfo(1)
    # table.sendMsgTableInfo(2)
    # table.sendMsgTableInfo(3)
    table.setTableType("create")

    # if table.isCountByBase():
    #     # TODO 自建桌最终结算 按玩家底分算 低分<=0 over
    #     ftlog.debug(':isOverByCardScore')
    #     table.sendCreateExtendBudgetsInfo(0)
        
    # if table.isPlaying():
    #     while table.curState() != MTableState.TABLE_STATE_GAME_OVER:
    #         #time.sleep(0.3)
    #         if not handler.doAutoAction():
    #             cmd = raw_input('action:')
    #             handler.processAction(cmd, table)

