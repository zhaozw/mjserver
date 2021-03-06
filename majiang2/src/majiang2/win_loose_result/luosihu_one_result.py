# -*- coding=utf-8
'''
Created on 2016年9月23日

一条和牌结果

@author: dongwei
'''
from majiang2.player.player import MPlayerTileGang
from majiang2.win_loose_result.one_result import MOneResult
from majiang2.tile.tile import MTile
from majiang2.table.table_config_define import MTDefine
from majiang2.player.hand.hand import MHand
from majiang2.table_tile.table_tile_factory import MTableTileFactory
from majiang2.win_rule.win_rule_factory import MWinRuleFactory
from majiang2.tile_pattern_checker.tile_pattern_checker_factory import MTilePatternCheckerFactory
#from majiang2.win_rule.win_rule import MWinRule
from majiang2.ai.play_mode import MPlayMode
#from majiang2.ting_rule.ting_rule_factory import MTingRuleFactory
#from majiang2.ai.ting import MTing
from freetime.util import log as ftlog
import copy
class MLuosihuOneResult(MOneResult):

    QINGYISE = 'qingyise'
    QINGYISENOGANG = 'qingyisenogang'
    YIPAOSHUANGXIANG = 'yipaoshuangxiang'
    QIDUI = 'qidui'
    QIDUIHAO = 'qiduihao'
    PENGPENGHU = 'pengpenghu'
    GANGKAI = 'gangkai'
    QIANGGANG = 'qiangGang'
    GANGSHANGPAO = 'gangshangpao'
    TIANHU = 'TIANHU'
    DIHU = 'DIHU'
    JINGOUDIAO = 'JINGOUDIAO'
    JIANGDUI = 'JIANGDUI'
    SHISANYAO = 'shisanyao'
    YAOJIU = 'yaojiu'
    DUANYAOJIU = 'duanyaojiu'
    GEN = 'gen'
    LIANGGANGMANFAN = 'lianggangmanfan'
    ZIMOJIAFAN = 'zimojiafan'
    MENQING = 'menqing'
    HAIDILAO = 'haidilao'
    QINGYISEPENGPENGHU = 'qingyisepengpenghu'
    QINGQIDUI = 'qingqidui'
    QINGQIDUIHAO = 'qingqiduihao'
    JIANGQIDUI = 'jiangqidui'
    JINGOUHU = 'jingouhu'
    HAIDIPAO = 'haidipao'
    ZIMO = 'zimo'
    def __init__(self):
        super(MLuosihuOneResult, self).__init__()
        self.__fan_xing = {
            # 赢的番型
            self.QINGYISE: {"name":"清一色", "index": 2},
	    self.QINGYISENOGANG:{"name":"清一色无杠", "index": 1},
            self.QIDUI: {"name":"七对", "index": 2},
            self.QIDUIHAO: {"name":"豪华七对", "index": 3},
            self.PENGPENGHU: {"name":"碰碰胡", "index": 1},
            self.TIANHU: {"name": "天胡", "index": 5},
            self.DIHU: {"name": "地胡", "index": 5},
            self.JINGOUDIAO:{"name":"金钩钓","index":1},
            self.JINGOUHU:{"name":"金钩胡","index":1},
            self.JIANGDUI:{"name":"将对","index":2},
	    self.YAOJIU:{"name":"幺九","index":2},
	    self.DUANYAOJIU:{"name":"断幺九","index":1},
            self.GANGKAI: {"name":"杠上开花", "index": 1},
            self.QIANGGANG: {"name":"抢杠胡", "index": 1},
            self.SHISANYAO:{"name":"十三幺", "index":4},
            self.GEN:{"name":"根", "index":1},
	    self.MENQING:{"name":"门清","index":1},
   	    self.LIANGGANGMANFAN:{"name":"两杠满番","index":1},
            self.HAIDIPAO: {"name":"海底炮", "index": 1},
            self.ZIMOJIAFAN:{"name":"自摸加番","index":1},
            self.GANGSHANGPAO: {"name":"杠上炮", "index": 1},
            self.YIPAOSHUANGXIANG: {"name":"一炮双响", "index": 1},
            self.HAIDILAO: {"name":"海底捞", "index": 1},
            self.QINGYISEPENGPENGHU:{"name":"清一色碰碰胡","index":3},
            self.QINGQIDUI:{"name":"清七对","index":3},
            self.JIANGQIDUI:{"name":"将七对","index":4},
            self.QINGQIDUIHAO:{"name":"清龙七对","index":4},
	    self.ZIMO:{"name":"自摸","index":0}
        }

    @property
    def fanXing(self):
        return self.__fan_xing

    def calcScore(self,gangScores = None):
        """计算输赢数值"""
        '''
        ps:房间信息配置选项maxFan 描述为最大分
        例如:8番封顶---maxFan=3
            16番封顶---maxFan=4
            32番封顶---maxFan=5
        '''

        # 序列化，以备后续的查找核实
        self.serialize()
        
        if self.resultType == self.RESULT_GANG:
            self.calcGang()
        elif self.resultType == self.RESULT_WIN:
            # 放在这里补充环境数据，要么不方便单元测试
            # self.__player_ting_liang = [False for _ in range(self.playerCount)]
            playersAllTiles = [[] for _ in range(self.playerCount)]

            for player in self.tableTileMgr.players:
                playersAllTiles[player.curSeatId] = player.copyTiles()
                # self.__player_ting_liang[player.curSeatId] = player.isTingLiang()

            # ftlog.info('MLuosihuOneResult.calcScore __player_ting_liang=', self.__player_ting_liang)

            self.__win_rule_mgr = MWinRuleFactory.getWinRule(MPlayMode.LUOSIHU)
            self.__win_patterns = [[] for _ in range(self.playerCount)]
            if self.winSeats == None:
                self.setWinSeats([self.winSeatId])
            for winSeatId in self.winSeats:
                self.__tile_pattern_checker = MTilePatternCheckerFactory.getTilePatternChecker(MPlayMode.LUOSIHU)
                self.__tile_pattern_checker.initChecker(playersAllTiles, self.winTile, self.tableTileMgr, False, self.lastSeatId, winSeatId, self.actionID)
                tiles = {MHand.TYPE_HAND: self.__tile_pattern_checker.playerHandTilesWithHu[winSeatId]}
                ftlog.info('MLuosihuOneResult.calcScore tiles=',tiles) 
                winResult, winPattern = self.__win_rule_mgr.getHuPattern(tiles)
                ftlog.info('MLuosihuOneResult.calcScore winPatterns=', winPattern)
                # 此处有坑，winPattern只有一种牌型，似乎优先一样的牌，比如：[14,14,14,15,15,16,16,16,19,19,19,20,20]，最后抓15
                # 如果卡五星比碰碰胡番数高，此处应该算卡五星，所以isHu应该返回所有可能的胡的牌型，结算时计算最优的番型
                # 此处预留isHu的修改
                # 此处不用winNodes主要原因是，卡五星可以不听/亮牌，直接胡
                self.__win_patterns[winSeatId] = [winPattern]
                ftlog.info('MLuosihuOneResult.calcScore __win_patterns=', self.__win_patterns)
                ftlog.info('MLuosihuOneResult.calcScore __winSeatId=', winSeatId)
            self.calcWin(self.winSeats,playersAllTiles)
        elif self.resultType == self.RESULT_FLOW:
            # self.__player_ting_liang = [False for _ in range(self.playerCount)]
            playersAllTiles = [[] for _ in range(self.playerCount)]

            for player in self.tableTileMgr.players:
                playersAllTiles[player.curSeatId] = player.copyTiles()
                # self.__player_ting_liang[player.curSeatId] = player.isTingLiang()
            self.calcFlow(gangScores)

    def calcGang(self):
        """计算杠的输赢"""
        # 杠分明杠、暗杠，明杠又分蓄杠（碰+最后一张自摸）和放杠（最后一张杠）
        # 暗杠整体2倍，蓄杠整体1倍，放杠出牌人2倍
        resultStat = [[] for _ in range(self.playerCount)]
        
        self.results[self.KEY_TYPE] = MOneResult.KEY_TYPE_NAME_GANG
        base = self.tableConfig.get(MTDefine.GANG_BASE, 1)
        ftlog.info('MLuosihuOneResult.calcGang GANG_BASE:', base)
        self.results[self.KEY_FAN_PATTERN] = [[] for _ in range(self.playerCount)]
        if self.style == MPlayerTileGang.AN_GANG:
            self.results[self.KEY_NAME] = "暗杠"
            self.results[self.KEY_FAN_PATTERN][self.winSeatId] = [["暗杠", "2番"]]
            resultStat[self.winSeatId].append({MOneResult.STAT_ANGANG:1})
            base *= 2
        else:
            if self.lastSeatId != self.winSeatId:
                self.results[self.KEY_NAME] = "明杠"
                self.results[self.KEY_FAN_PATTERN][self.lastSeatId] = [["放杠", "2番"]]
                self.results[self.KEY_FAN_PATTERN][self.winSeatId] = [["明杠", "2番"]]
                base *= 2
            else:
                # 这种情况一定是碰牌后，自摸杠牌
                # 卡五星当中，碰牌后自摸，称为蓄杠（其他地方还叫明杠）
                self.results[self.KEY_NAME] = "蓄杠"
                self.results[self.KEY_FAN_PATTERN][self.winSeatId] = [["蓄杠", "1番"]]

            resultStat[self.winSeatId].append({MOneResult.STAT_MINGGANG:1})
        resultStat[self.winSeatId].append({MOneResult.STAT_GANG:1})
         
        # 处理杠上杠的分数
        totalGangArray = []
        for i in range(self.playerCount):
            gangArray = self.tableTileMgr.players[i].copyGangArray()
            for j in range(len(gangArray)):
                gangArray[j]['seatId'] = i
            totalGangArray.extend(gangArray)
        totalGangArray = sorted(totalGangArray , key=lambda _gangArray: _gangArray['actionID'], reverse = True)
        
        curActionId =  self.actionID
        curCalcSeatId = self.winSeatId
        combo = 1
        for gang in totalGangArray:
            ftlog.debug('calcGang info:',gang)
            if gang.has_key('styleScore') and gang['styleScore'] and gang['actionID']:
                if curActionId - gang['actionID'] > 3:
                    break
                if gang['seatId'] == curCalcSeatId:
                    # 找到当前杠牌的人的上一次杠，如果是本人，actionID差值为2，1是抓牌，另1是杠牌
                    if gang['actionID'] == (curActionId - 2):
                        curActionId = gang['actionID']
                        curCalcSeatId = gang['seatId']
                        combo = combo * 2
                        ftlog.debug('calcGang info:',curActionId, combo, base)
        if combo > 1:
            ftlog.debug('calcGang info:',combo, base)
            # 杠上杠分数为前一杠的2倍(蓄杠为一倍)，如果第三次杠，其实就是4倍
            if self.playMode == 'luosihu-luosihu' and self.tableConfig.get(MTDefine.GANGSHANGGANG, 0):
                if self.style == MPlayerTileGang.MING_GANG and self.lastSeatId == self.winSeatId:
                    base = base * combo
                else:
                    base = base * combo
                # 覆盖本身杠牌类型数据
                fan = str(base) + "番"
                self.results[self.KEY_FAN_PATTERN][self.winSeatId] = [["杠上杠", fan]]

	scores = [0 for _ in range(self.playerCount)]
        # 放杠，放杠一定是明杠
        if self.lastSeatId != self.winSeatId:
            # 明杠, 只有放杠和明杠两家改分
            scores[self.lastSeatId] = -base
            scores[self.winSeatId] = base
        else:
            # 暗杠+蓄杠, 所有输家扣分
	    #modify by yj 05.05
	    for seatId in range(self.playerCount):
	        #if self.playMode == 'luosihu-xuezhan' or self.playMode == 'luosihu-ctxuezhan':
	        if self.playMode == 'luosihu-ctxuezhan':
                    if seatId!=self.winSeatId and not self.tableTileMgr.players[seatId].isWon():
	                scores[seatId] = -base
	                scores[self.winSeatId]+=base
		else:
            	    scores = [-base for _ in range(self.playerCount)]
                    scores[self.winSeatId] = (self.playerCount - 1) * base      
	if self.playMode == 'luosihu-xuezhan' or self.playMode == 'luosihu-luosihu':
	    scores = [0 for _ in range(self.playerCount)]
        self.results[self.KEY_SCORE] = scores
        self.results[self.KEY_GANG_STYLE_SCORE] = base
        self.results[self.KEY_STAT] = resultStat

    def calcWin(self, winSeats, playersAllTiles):
        """螺丝胡算番规则"""

        maxFan = self.tableConfig.get(MTDefine.MAX_FAN, 0)
        score = [0 for _ in range(self.playerCount)]
        self.results[self.KEY_FAN_PATTERN] = [[] for _ in range(self.playerCount)]
        # 目前从前端代码上看，winMode只能区分：平胡（非自摸和牌），自摸，点炮
        self.results[self.KEY_WIN_MODE] = [MOneResult.WIN_MODE_LOSS for _ in range(self.playerCount)]
        self.results[self.KEY_STAT] = [[] for _ in range(self.playerCount)]
        for winSeatId in winSeats:
            self.__tile_pattern_checker = MTilePatternCheckerFactory.getTilePatternChecker(MPlayMode.LUOSIHU)
            self.__tile_pattern_checker.initChecker(playersAllTiles, self.winTile, self.tableTileMgr, False, self.lastSeatId, winSeatId, self.actionID)
            winnerResult = self.getWinnerResults(winSeatId)
            if self.lastSeatId != winSeatId:
                # 放炮和牌
                finalResult = []
                paoResult = self.getPaoResults()
                finalResult.extend(winnerResult)
                finalResult.extend(paoResult)
                finalResult.extend(self.getLooserResults(winSeatId,self.lastSeatId))
                winScore = self.getScoreByResults(finalResult, maxFan)
                score[self.lastSeatId] -= winScore
                score[winSeatId] = winScore
                if self.playMode == 'luosihu-ctxuezhan' and self.tableConfig.get(MTDefine.HUJIAOZHUANYI, 0) and paoResult:
		    player = self.tableTileMgr.players[self.lastSeatId]
                    gangCount = len(player.gangTiles)
                    score[self.lastSeatId] -= player.gangTiles[gangCount - 1].styleScore
                    score[winSeatId] += player.gangTiles[gangCount - 1].styleScore
		    ftlog.debug('MLuosihuOneResult.calcWin hujiaozhuanyi score:',player.gangTiles[gangCount - 1].styleScore)
                # piaoScore = self.piaoProcessor.getPiaoPointsBySeats(winSeatId, self.lastSeatId)
                # score[self.lastSeatId] -= piaoScore
                # score[winSeatId] += piaoScore
            else:
                # 自摸胡牌
                winScore = 0
                looserResults = [[] for _ in range(self.playerCount)]
                for seatId in range(len(score)):
                    finalResult = []
                    if seatId != winSeatId:
                        #if self.playMode == 'luosihu-xuezhan' or self.playMode == 'luosihu-ctxuezhan':
			if self.playMode == 'luosihu-ctxuezhan':
			    if not self.tableTileMgr.players[seatId].isWon():    
                                finalResult.extend(winnerResult)
                                ftlog.info('MLuosihuOneResult.calcWin mingbaishu info 1:', looserResults, seatId)
                                looserResult = self.getLooserResults(winSeatId,seatId)
                                finalResult.extend(looserResult)
                                looserResults[seatId] = looserResult
                                tableScore = self.getScoreByResults(finalResult, maxFan)
				
				if self.tableConfig.get(MTDefine.ZIMOJIAFEN, 1) == 2:
                                    winBase = self.tableConfig.get(MTDefine.WIN_BASE, 1)
                                    if tableScore + winBase <= maxFan:
					tableScore += winBase

                                if self.gangKai and self.tableConfig.get(MTDefine.DIANGANGHUA, 1) == 2:
                                    gangFromSeatId = self.tableTileMgr.players[winSeatId].gangTilesFromSeat
                                    if len(gangFromSeatId) > 0 and gangFromSeatId[-1]['playerSeatId'] != winSeatId:
                                        if seatId != gangFromSeatId[-1]['playerSeatId']:
                                            tableScore = 0
				
                                score[seatId] = -tableScore
                                winScore += tableScore
                        else:
	                    finalResult.extend(winnerResult)
                            ftlog.info('MLuosihuOneResult.calcWin mingbaishu info 2:', looserResults, seatId)
                            looserResult = self.getLooserResults(winSeatId,seatId)
                            finalResult.extend(looserResult)
                            looserResults[seatId] = looserResult
                            tableScore = self.getScoreByResults(finalResult, maxFan)
                            score[seatId] = -tableScore
                            winScore += tableScore
                        # piaoScore = self.piaoProcessor.getPiaoPointsBySeats(winSeatId, seatId)
                        # score[seatId] -= piaoScore
                        # winScore += piaoScore
                score[winSeatId] = winScore
            ftlog.info('MLuosihuOneResult.calcWin score:', score)

            self.results[self.KEY_FAN_PATTERN][winSeatId] = self.getFanPatternListByResults(winnerResult)
            if winSeatId == self.lastSeatId:
                # 自摸
                self.results[self.KEY_WIN_MODE][winSeatId] = MOneResult.WIN_MODE_ZIMO
                # 自摸者自摸+1
                self.results[self.KEY_STAT][winSeatId].append({MOneResult.STAT_ZIMO:1})
                # 输牌的人的特殊番型
                if looserResults:
                    for seatId in range(self.playerCount):
                        if seatId != winSeatId:
                            self.results[self.KEY_FAN_PATTERN][seatId] = self.getFanPatternListByResults(looserResults[seatId])
                        if len(winSeats) > 1:
                            paoResult.append({'name':'一炮双响', "index":0, "score":0, 'fanSymbol':''})
            else:
                # 点炮，赢的人平胡
	        if self.qiangGang:
                    self.results[self.KEY_WIN_MODE][winSeatId] = MOneResult.WIN_MODE_QIANGGANGHU
                else:
                    self.results[self.KEY_WIN_MODE][winSeatId] = MOneResult.WIN_MODE_PINGHU
                # 点炮，放跑者标为点炮
                self.results[self.KEY_WIN_MODE][self.lastSeatId] = MOneResult.WIN_MODE_DIANPAO
                ftlog.info('MYunnanOneResult calcScore: ', self.lastSeatId, winSeatId)
                # 点炮，输的人的番型
                if len(winSeats) > 1:
                    paoResult.append({'name':'一炮双响', "index":0, "score":0, 'fanSymbol':''})
                if self.piaoProcessor.isPiao and self.piaoProcessor.piaoPoints[self.lastSeatId]:
                    paoResult.append({'name':'加'+str(self.piaoProcessor.piaoPoints[self.lastSeatId])+'漂', "index":0, "score":0, 'fanSymbol':''})
		if self.playMode == 'luosihu-ctxuezhan':
                    paoResult.append({'name':'点炮', "index":0, "score":0, 'fanSymbol':''})
                self.results[self.KEY_FAN_PATTERN][self.lastSeatId] = self.getFanPatternListByResults(paoResult)
                # 点炮,点炮者点炮+1
                self.results[self.KEY_STAT][self.lastSeatId].append({MOneResult.STAT_DIANPAO:1})
            # 最大番,当前的赢家番数,如果超过封顶,也显示原始番数
            self.results[self.KEY_STAT][winSeatId].append({MOneResult.STAT_ZUIDAFAN:self.getFanByResults(winnerResult)})

        self.results[self.KEY_SCORE] = score
        # 只有一种KEY_NAME不合理，名称的优先级根据需求再加
        self.results[self.KEY_NAME] = MOneResult.KEY_TYPE_NAME_HU
        self.results[self.KEY_TYPE] = MOneResult.KEY_TYPE_NAME_HU

        ftlog.info('MYunnanOneResult calcScore:KEY_SCORE:', self.results[self.KEY_SCORE])
        ftlog.info('MYunnanOneResult calcScore:KEY_NAME:', self.results[self.KEY_NAME])
        ftlog.info('MYunnanOneResult calcScore:KEY_TYPE:', self.results[self.KEY_TYPE])
        ftlog.info('MYunnanOneResult calcScore:KEY_WIN_MODE:', self.results[self.KEY_WIN_MODE])
        ftlog.info('MYunnanOneResult calcScore:KEY_FAN_PATTERN:', self.results[self.KEY_FAN_PATTERN])
        ftlog.info('MYunnanOneResult calcScore:KEY_STAT:', self.results[self.KEY_STAT]) 

    def calcPigsScore(self, pigInfo, score):
        """计算查花猪的分数"""
        if pigInfo.has_key('pigs') \
                and pigInfo.has_key('playerCount') \
                and pigInfo.has_key('scoreBase') \
                and pigInfo.has_key('fanMax') \
                and pigInfo.has_key('huSeats'):
            pigs = pigInfo['pigs']
            playerCount = pigInfo['playerCount']
            fanMax = pigInfo['fanMax']
            scoreBase = pigInfo['scoreBase']
            huSeats = pigInfo['huSeats']
            ftlog.debug("calcPigsScore pigInfo pigs:", pigs
                        , "playerCount:", playerCount
                        , "fanMax:", fanMax
                        , "scoreBase:", scoreBase
                        , "huSeats:", huSeats
                        , "score:", score)
            if playerCount != len(score):
                ftlog.debug("calcPigsScore playerCount!=len(score) error playerCount:", playerCount, 'score:', score)
                return
            for pig in pigs:
                if pig in huSeats:
                    ftlog.debug("calcPigsScore error pig hasHu pigs:", pigs, 'huSeats:', huSeats)
                    return
                    # 遍历花猪不检查是否胡牌,因为计算花猪时就要排除
            for pig in pigs:
                for index in range(playerCount):
                    if index in huSeats:
                        continue
                    else:
                        if index not in pigs:
                            score[index] += fanMax
                            score[pig] -= fanMax
            ftlog.debug("calcPigsScore score:", score)
        else:
            ftlog.debug("calcPigsScore pigInfo error, pigInfo:", pigInfo)
            return


    def calcGangBase(self, actionId):
        # 处理杠上杠的分数
        _curActionId = actionId
        for i in range(self.playerCount):
            gangArray = self.tableTileMgr.players[i].copyGangArray()
            ftlog.debug(gangArray)
            for gang in gangArray:
                if gang.has_key('styleScore') and gang['styleScore'] and gang['actionID']:
                    if i == self.winSeatId:
                        # 找到当前杠牌的人的上一次杠，如果是本人，actionID差值为2，1是抓牌，另1是杠牌
                        if gang['actionID'] == (_curActionId - 2):
                            base = base * 2
                    else:
                        if gang['actionID'] == (_curActionId - 3):
                            base = base * 2

    def calcFlow(self,gangScores = None):
        """螺丝胡计算流局"""
	ftlog.debug('calcFlow.self.playMode=',self.playMode)
        self.__win_rule_mgr = MWinRuleFactory.getWinRule(self.playMode)
        self.__win_rule_mgr.setTableTileMgr(self.tableTileMgr)
        score = [0 for _ in range(self.playerCount)]
        tingPlayers = []
        untingPlayers = []
	hasHuPlayer = []
        for player in self.tableTileMgr.players:
            allTiles = player.copyTiles()
            ftlog.info('calcFlow tiles info:', allTiles)
            winResult = False
            for tile in range(MTile.TILE_MAX_VALUE):
                newTile = MTile.cloneTiles(allTiles)
                newTile[MHand.TYPE_HAND].append(tile)
                winResult, winPattern,_= self.__win_rule_mgr.isHu(newTile, tile, True, self.tableTileMgr.getMagicTiles(player.isTing()), [], [], 0, 0, 0)
                if winResult:
                    break
	    if self.playMode == 'luosihu-ctxuezhan' or self.playMode == 'luosihu-xuezhan':
                absenceColor = player.absenceColor
                tileArr = MTile.changeTilesToValueArr(player.handTiles)
                if MTile.getTileCountByColor(tileArr, absenceColor) > 0:
                    winResult = False
		ftlog.debug('calcFlow absenceColor=',absenceColor,' getTileCountByColor=',MTile.getTileCountByColor(tileArr, absenceColor),' winResult=',winResult)
            if winResult:
		if not player.isWon():
                    tingPlayers.append(player)
            else:
                untingPlayers.append(player)
	    if player.isWon():
		hasHuPlayer.append(player)
        tingCount = len(tingPlayers)
        untingCount = len(untingPlayers)
	
	winMode = [MOneResult.WIN_MODE_LOSS for _ in range(self.playerCount)]
	maxFan = self.tableConfig.get(MTDefine.MAX_FAN, 0)	
	winBase = self.tableConfig.get(MTDefine.WIN_BASE, 1)
        playersAllTiles = [[] for _ in range(self.playerCount)]
        for player in self.tableTileMgr.players:
            playersAllTiles[player.curSeatId] = self.playerAllTiles[player.curSeatId]
	pigs = []	
        if self.playMode == 'luosihu-ctxuezhan' or self.playMode == 'luosihu-xuezhan':
            colorState = [0 for _ in range(self.playerCount)]
            # 得到手牌
            for seatId in range(self.playerCount):
                colorState[seatId] = MTile.getColorCount(MTile.changeTilesToValueArr(playersAllTiles[seatId][MHand.TYPE_HAND]))

            huSeats = []
            for player in self.tableTileMgr.players:
                if player.isWon():
                    huSeats.append(player.curSeatId)
            for seatId in range(self.playerCount):
                if colorState[seatId] >= 3:
                    pigs.append(seatId)
	    ftlog.debug("MLuosihuOneResult calcFlow calcPigsScore pigs:",pigs,len(pigs))
	    
            if len(pigs) > 0:
                for pig in pigs:
                    if pig in huSeats:
                        ftlog.debug("calcPigsScore error pig hasHu pigs:", pigs, 'huSeats:', huSeats)
                        return
                        # 遍历花猪不检查是否胡牌,因为计算花猪时就要排除
                for pig in pigs:
                    for index in range(self.playerCount):
			'''
                        if index in huSeats:
                            continue
                        else:
			'''
                        if index not in pigs:
                            score[index] += maxFan
                            score[pig] -= maxFan
                            winMode[pig] = MOneResult.WIN_MODE_CHAHUAZHU           

                ftlog.debug("MLuosihuOneResult calcFlow calcPigsScore score:", score)
	
        if self.playMode == 'luosihu-xuezhan' or self.playMode == 'luosihu-ctxuezhan' or self.playMode == 'luosihu-luosihu':
	    # and self.getWinPlayerCount() == 0:
            tingSeatToScore={}

            self.__win_patterns = [[] for _ in range(self.playerCount)]
            losePlayers = []
            if untingCount < self.playerCount and untingCount != 0:
                if untingCount != 0:
                    losePlayers.extend(untingPlayers)
		    for loseplayer in losePlayers:
			if self.playMode == 'luosihu-ctxuezhan' or self.playMode == 'luosihu-xuezhan':
			    if gangScores[loseplayer.curSeatId][loseplayer.curSeatId] > 0 :
			        score[loseplayer.curSeatId]-= gangScores[loseplayer.curSeatId][loseplayer.curSeatId]
			    for player in self.tableTileMgr.players:
			        if player.curSeatId != loseplayer.curSeatId:
			            score[player.curSeatId]-=gangScores[loseplayer.curSeatId][player.curSeatId]
                else:
                    for player in tingPlayers:
                        losePlayers.append(player)
                        tingPlayers.remove(player)
		ftlog.info('calcFlow losePlayers=',losePlayers, ' tingPlayers',tingPlayers,' pigs',pigs)
                for player in tingPlayers:
                    allTiles = player.copyTiles()
                    tmp_score = 0
                    for tile in range(MTile.TILE_MAX_VALUE):
                        newTile = MTile.cloneTiles(allTiles)
                        newTile[MHand.TYPE_HAND].append(tile)
                        # 测试听牌时，默认听牌状态
                        winResult, winPattern,_ = self.__win_rule_mgr.isHu(newTile, tile, True, self.tableTileMgr.getMagicTiles(player.isTing()), [], [], 0, 0, 0)
                        ftlog.info('calcFlow winResult info:',tile, winResult)
                        if winResult:
                            self.__win_patterns[player.curSeatId] = [winPattern]
                            playersAllTiles[player.curSeatId][MHand.TYPE_CUR] = [tile]
                            self.__tile_pattern_checker = MTilePatternCheckerFactory.getTilePatternChecker(MPlayMode.LUOSIHU)
                            self.__tile_pattern_checker.initChecker(playersAllTiles, tile, self.tableTileMgr, False, self.lastSeatId, player.curSeatId, self.actionID)
                            self.__tile_pattern_checker.setWinSeatId(player.curSeatId)
                            self.__tile_pattern_checker.setWinTile(tile)
                            winnerResult = self.getWinnerResults(player.curSeatId, True)
                            finalResult = []
                            finalResult.extend(winnerResult)
                            winScore = self.getScoreByResults(finalResult, maxFan)
                            if tmp_score == 0 or tmp_score < winScore :
                                tmp_score = winScore
			    if self.playMode == 'luosihu-luosihu':
				tmp_score = 1
			    ftlog.info('calcFlow winResult winMode:',winMode,player.curSeatId,' tmp_score=',tmp_score )
                    for losePlayer in losePlayers:
			if not losePlayer.curSeatId in pigs:
                            score[losePlayer.curSeatId] -= tmp_score
                            score[player.curSeatId] += tmp_score
                            winMode[losePlayer.curSeatId] = MOneResult.WIN_MODE_CHADAJIAO
                            ftlog.info('calcFlow losePlayer.curSeatId:', losePlayer.curSeatId,' tmp_score:',tmp_score,' score:',score)
		if self.playMode == 'luosihu-luosihu':
		    if len(losePlayers) > 0:
			tmp_score = 1
			for player in hasHuPlayer:
	                    score[player.curSeatId] += tmp_score * len(losePlayers)
			for losePlayer in losePlayers:
			    score[losePlayer.curSeatId] -= tmp_score * len(hasHuPlayer)
			    winMode[losePlayer.curSeatId] = MOneResult.WIN_MODE_CHADAJIAO
 
        ftlog.info('calcFlow score info', score)
        self.results[self.KEY_SCORE] = score
        self.results[self.KEY_TYPE] = MOneResult.KEY_TYPE_NAME_FLOW
        self.results[self.KEY_NAME] = MOneResult.KEY_TYPE_NAME_FLOW
        #winMode = [MOneResult.WIN_MODE_LOSS for _ in range(self.playerCount)]
        self.results[self.KEY_WIN_MODE] = winMode
	ftlog.info('calcFlow winResult winMode:',winMode)
        resultStat = [[] for _ in range(self.playerCount)]
        self.results[self.KEY_STAT] = resultStat
        fanPattern = [[] for _ in range(self.playerCount)]
        self.results[self.KEY_FAN_PATTERN] = fanPattern

    def getWinPlayerCount(self):
        count = 0
        for player in self.tableTileMgr.players:
            if player.isWon():
                count += 1
        return count


    def getWinnerResults(self,winSeatId, isFlow=False):
        """和牌时，计算胜者的牌对整个牌桌的分数影响"""
        winnerResults = []
        if self.playMode == 'luosihu-ctxuezhan':
            return self.getWinnerResultsForXueZhanDaoDi(winSeatId, isFlow)
        elif self.playMode == 'luosihu-xuezhan':
            return self.getWinnerResultsForLuoSiHuXueZhan(winSeatId, isFlow)
        elif self.playMode == 'luosihu-luosihu':
            return self.getWinnerResultsForLuoSiHu(winSeatId, isFlow)
        else:
            return self.getWinnerResultsForLuoSiHuXueZhan(winSeatId, isFlow)
        return winnerResults

    def getWinnerResultsForXueZhanDaoDi(self,winSeatId, isFlow=False):
        # 血战到底
        """和牌时，计算胜者的牌对整个牌桌的分数影响"""
        winnerResults = []
        # 不需要根据和牌牌型计算的番型，先计算
	maxFan = self.tableConfig.get(MTDefine.MAX_FAN, 0)

        """自摸加番 1番"""
	
        if self.lastSeatId == winSeatId :
            if self.tableConfig.get(MTDefine.ZIMOJIAFEN, 0) == 1:
                winnerResults.append(self.processFanXingResult(self.ZIMOJIAFAN))
	
        """杠开 1番"""
        if self.gangKai:
            winnerResults.append(self.processFanXingResult(self.GANGKAI))
        """抢杠胡 1番"""
        if self.qiangGang:
            winnerResults.append(self.processFanXingResult(self.QIANGGANG))
	for pattern in self.__win_patterns[winSeatId]:
            """根的番计算 龙七对,清龙七对 根要减1"""
            hasGen, winnerGen = self.getWinnerGen()
            if hasGen:
                if self.__tile_pattern_checker.isQiduiHao(pattern):
                    winnerGen -= 1
                winnerResults.append(self.processFanXingResult(self.GEN,0,winnerGen))
            """金钩胡 1番 不和对对胡一起算"""
            if self.checkDaDiaoChe() and not self.__tile_pattern_checker.isPengpenghu(pattern):
                winnerResults.append(self.processFanXingResult(self.JINGOUHU)) 
	
        """门清 1番"""
	if self.tableConfig.get(MTDefine.MEN_CLEAR_DOUBLE, 0):
            if self.checkMenQing():
                winnerResults.append(self.processFanXingResult(self.MENQING))
            """断幺九 中张 1番"""
            if self.isDuanYaoJiu():
                winnerResults.append(self.processFanXingResult(self.DUANYAOJIU))
        """天胡 满番"""
	if self.tableConfig.get(MTDefine.TIAN_HU,0):
            if self.isTianHu():
                self.fanXing[self.TIANHU]["index"] = maxFan
                winnerResults.append(self.processFanXingResult(self.TIANHU))
	"""地胡 满番"""
	if self.tableConfig.get(MTDefine.DI_HU,0):
            if self.isDiHu():
                self.fanXing[self.DIHU]["index"] = maxFan
                winnerResults.append(self.processFanXingResult(self.DIHU))
        if self.lastSeatId == winSeatId :
            winnerResults.append(self.processFanXingResult(self.ZIMO))
	'''
        """海底捞 扫地胡 1番"""
        if isFlow == False:
            if self.isHaidilao():
                winnerResults.append(self.processFanXingResult(self.HAIDILAO))
        """海底炮 1番"""
        if self.__tile_pattern_checker.isHaidipao():
            winnerResults.append(self.processFanXingResult(self.HAIDIPAO))
	'''
        # 个别番型和和牌牌型有关，算分时选取分数最大的情况
        maxPatternScore = 0
        bestWinnerResultsByPattern = []
	ftlog.info('MLuosihuOneResult.getWinnerResults xxx winnerResults=',winnerResults)
        ftlog.info('MLuosihuOneResult.getWinnerResults winSeatId', self.__win_patterns[winSeatId])
        for pattern in self.__win_patterns[winSeatId]:
            ftlog.info('MLuosihuOneResult.getWinnerResults win_pattern=', pattern)

            # pattern内，全部是手牌(包含最后一张牌)
            eachWinnerResultsByPattern = []
            """碰碰胡 2番"""
            if self.__tile_pattern_checker.isPengpenghu(pattern):
                self.fanXing[self.PENGPENGHU]["index"] = 2
                eachWinnerResultsByPattern.append(self.processFanXingResult(self.PENGPENGHU))
            """清一色 2番"""
            if self.__tile_pattern_checker.isQingyise():
                eachWinnerResultsByPattern.append(self.processFanXingResult(self.QINGYISE))
            """清一色碰碰胡 3番"""
            if self.__tile_pattern_checker.isPengpenghu(pattern) and self.__tile_pattern_checker.isQingyise():
                eachWinnerResultsByPattern.append(self.processFanXingResult(self.QINGYISEPENGPENGHU))
            """七对 2番"""
            if self.__tile_pattern_checker.isQidui(pattern):
	        eachWinnerResultsByPattern.append(self.processFanXingResult(self.QIDUI))
            """清七对 3番"""
            if self.__tile_pattern_checker.isQingyise() and self.__tile_pattern_checker.isQidui(pattern):
                eachWinnerResultsByPattern.append(self.processFanXingResult(self.QINGQIDUI))
            """龙七对 3番"""
            if self.__tile_pattern_checker.isQiduiHao(pattern):
                eachWinnerResultsByPattern.append(self.processFanXingResult(self.QIDUIHAO))
            """清龙七对 4番"""
            if self.__tile_pattern_checker.isQiduiHao(pattern) and self.__tile_pattern_checker.isQingyise():
                eachWinnerResultsByPattern.append(self.processFanXingResult(self.QINGQIDUIHAO))
            if self.tableConfig.get(MTDefine.JIANGDUI,0):
 	        """全幺九 3番"""
                if self.isYaoJiu(pattern):
                    #self.fanXing[self.YAOJIU]["index"] = 3
                    eachWinnerResultsByPattern.append(self.processFanXingResult(self.YAOJIU))
                """将对 3番"""
                if self.__tile_pattern_checker.isPengpenghu(pattern) and self.isJiangDui():
                    #self.fanXing[self.JIANGDUI]["index"] = 3
                    eachWinnerResultsByPattern.append(self.processFanXingResult(self.JIANGDUI))
            """将七对 4番"""
            if self.__tile_pattern_checker.isQiduiHao(pattern) and self.isJiangDui():
                eachWinnerResultsByPattern.append(self.processFanXingResult(self.JIANGQIDUI))

	       
            bestWinnerResult = []
            maxScore = 0
            for result in eachWinnerResultsByPattern:
		tempResult = []
		tempResult.append(result)
		calctempResult = []
		calctempResult.extend(tempResult)
                tempScore = self.getScoreByResults(calctempResult)
                if tempScore > maxScore:
                    maxScore = tempScore
                    bestWinnerResult = tempResult
	    ftlog.info('MLuosihuOneResult.getWinnerResults xxx bestWinnerResult=',bestWinnerResult)	    
            # 计算当前牌型的赢牌奖励分数，选取最大值的牌型
            calceachWinnerResultsByPattern = []
            #calceachWinnerResultsByPattern.extend(winnerResults)
            calceachWinnerResultsByPattern.extend(bestWinnerResult)
            tempScore = self.getScoreByResults(calceachWinnerResultsByPattern)
            if tempScore > maxPatternScore:
                # 分数相同就不管了
                maxPatternScore = tempScore
                bestWinnerResultsByPattern = calceachWinnerResultsByPattern
	    ftlog.info('MLuosihuOneResult.getWinnerResults xxx bestWinnerResultsByPattern=',bestWinnerResultsByPattern)
        winnerResults.extend(bestWinnerResultsByPattern)
        ftlog.info('MLuosihuOneResult.getWinnerResults xuezhandaodi winnerResults=', winnerResults)

        return winnerResults

    def getWinnerResultsForLuoSiHu(self,winSeatId, isFlow=False):
        winnerResults = []
        """和牌时，计算胜者的牌对整个牌桌的分数影响"""
        # 不需要根据和牌牌型计算的番型，先计算
        maxFan = self.tableConfig.get(MTDefine.MAX_FAN, 0)
        """清一色"""
        if self.__tile_pattern_checker.isQingyise():
            self.fanXing[self.QINGYISE]["index"] = 1
            winnerResults.append(self.processFanXingResult(self.QINGYISE))
        """自摸加番"""
        if self.lastSeatId == winSeatId :
            if self.tableConfig.get(MTDefine.ZIMODOUBLE, 0):
                winnerResults.append(self.processFanXingResult(self.ZIMOJIAFAN))

        """杠开"""
        if self.gangKai:
            winnerResults.append(self.processFanXingResult(self.GANGKAI))
        """抢杠胡"""
        if self.qiangGang:
            if self.tableTileMgr.players[self.lastSeatId].isWon():
                self.fanXing[self.QIANGGANG]["index"] = 2
            winnerResults.append(self.processFanXingResult(self.QIANGGANG))
        
        """碰碰胡"""
	for pattern in self.__win_patterns[winSeatId]:
            if self.__tile_pattern_checker.isPengpenghu(pattern):
                if self.isJinGouDiao(True):
                    winnerResults.append(self.processFanXingResult(self.JINGOUDIAO,0,2))
                #else:
                #    winnerResults.append(self.processFanXingResult(self.PENGPENGHU))

        # 个别番型和和牌牌型有关，算分时选取分数最大的情况
        #winnerResultsByPattern = []
        maxPatternScore = 0
        bestWinnerResultsByPattern = []

        ftlog.info('MLuosihuOneResult.getWinnerResults winSeatId', self.__win_patterns[winSeatId])
        for pattern in self.__win_patterns[winSeatId]:
            ftlog.info('MLuosihuOneResult.getWinnerResults win_pattern=', pattern)

            # pattern内，全部是手牌(包含最后一张牌)
            eachWinnerResultsByPattern = []
            """七对"""
            if self.__tile_pattern_checker.isQidui(pattern):
		self.fanXing[self.QIDUI]["index"] = 1
                eachWinnerResultsByPattern.append(self.processFanXingResult(self.QIDUI))
            """豪华七对"""
            hu_tiles = self.tableTileMgr.players[winSeatId].copyHuArray()
            tempcount = 0
            if len(hu_tiles) > 0:
                handTiles = self.playerAllTiles[winSeatId][MHand.TYPE_HAND]
                tempcount = MTile.getTileCount(hu_tiles[-1],handTiles)
            ftlog.debug('MLuosihuOneResult.getWinnerResults hu_tiles=',hu_tiles,tempcount)
            if self.__tile_pattern_checker.isQiduiHao(pattern) and tempcount >= 3:
                self.fanXing[self.QIDUIHAO]["index"] = 2
                eachWinnerResultsByPattern.append(self.processFanXingResult(self.QIDUIHAO))
            ftlog.info('MLuosihuOneResult.getWinnerResults eachWinnerResultsByPattern=', eachWinnerResultsByPattern)
		
            bestWinnerResult = []
            maxScore = 0
            for result in eachWinnerResultsByPattern:
                tempResult = []
                tempResult.append(result)
                calctempResult = []
                calctempResult.extend(tempResult)
                tempScore = self.getScoreByResults(calctempResult)
                if tempScore > maxScore:
                    maxScore = tempScore
                    bestWinnerResult = tempResult 

            # 计算当前牌型的赢牌奖励分数，选取最大值的牌型
            calceachWinnerResultsByPattern = []
            #calceachWinnerResultsByPattern.extend(winnerResults)
            calceachWinnerResultsByPattern.extend(bestWinnerResult)
            tempScore = self.getScoreByResults(calceachWinnerResultsByPattern)
            if tempScore > maxPatternScore:
                # 分数相同就不管了
                maxPatternScore = tempScore
                bestWinnerResultsByPattern = calceachWinnerResultsByPattern

        winnerResults.extend(bestWinnerResultsByPattern)
        ftlog.info('MLuosihuOneResult.getWinnerResults luosihu winnerResults=', winnerResults)
        return winnerResults

    def getWinnerResultsForLuoSiHuXueZhan(self,winSeatId, isFlow=False):
        """和牌时，计算胜者的牌对整个牌桌的分数影响"""
        winnerResults = []
        # 不需要根据和牌牌型计算的番型，先计算
	maxFan = self.tableConfig.get(MTDefine.MAX_FAN, 0)

        """清一色 2番"""
	if self.__tile_pattern_checker.isQingyise():
            """清一色无杠 满番"""
            if self.getGangCount() == 0 :
	        self.fanXing[self.QINGYISENOGANG]["index"] = maxFan
                winnerResults.append(self.processFanXingResult(self.QINGYISENOGANG))
	    else:
                winnerResults.append(self.processFanXingResult(self.QINGYISE))
        """自摸加番 1番"""
        if self.lastSeatId == winSeatId :
            winnerResults.append(self.processFanXingResult(self.ZIMOJIAFAN))
        """杠开"""
        if self.gangKai:
            self.fanXing[self.GANGKAI]["index"] = maxFan
            winnerResults.append(self.processFanXingResult(self.GANGKAI))
        """抢杠胡"""
        if self.qiangGang:
            winnerResults.append(self.processFanXingResult(self.QIANGGANG))
	for pattern in self.__win_patterns[winSeatId]:
            """碰碰胡"""
            if self.__tile_pattern_checker.isPengpenghu(pattern):             
                if self.isJinGouDiao(True):
                    if self.getGangCount():
                        self.fanXing[self.JINGOUDIAO]["index"] = maxFan
                        winnerResults.append(self.processFanXingResult(self.JINGOUDIAO))
                    else:
                        winnerResults.append(self.processFanXingResult(self.JINGOUDIAO))
                if self.getGangCount():
                    self.fanXing[self.PENGPENGHU]["index"] = maxFan
                    winnerResults.append(self.processFanXingResult(self.PENGPENGHU))

        """两杠 满番"""
        if self.getGangCount() >= 2 and self.tableConfig.get(MTDefine.LIANGGANGMANFAN, 0):
            self.fanXing[self.LIANGGANGMANFAN]["index"] = maxFan
            winnerResults.append(self.processFanXingResult(self.LIANGGANGMANFAN))


        # 个别番型和和牌牌型有关，算分时选取分数最大的情况
        #winnerResultsByPattern = []
        maxPatternScore = 0
        bestWinnerResultsByPattern = []

        ftlog.info('MLuosihuOneResult.getWinnerResults winSeatId', self.__win_patterns[winSeatId])
        for pattern in self.__win_patterns[winSeatId]:
            ftlog.info('MLuosihuOneResult.getWinnerResults win_pattern=', pattern)

            # pattern内，全部是手牌(包含最后一张牌)
            eachWinnerResultsByPattern = []
            '''    
            """天胡 满番"""
            if self.isTianHu():
                self.fanXing[self.TIANHU]["index"] = maxFan
                eachWinnerResultsByPattern.append(self.processFanXingResult(self.TIANHU))        
            """地胡 满番"""
            if self.isDiHu():
                self.fanXing[self.DIHU]["index"] = maxFan
                eachWinnerResultsByPattern.append(self.processFanXingResult(self.DIHU))
	    '''
            """七对 2番"""
            if self.__tile_pattern_checker.isQidui(pattern):
                eachWinnerResultsByPattern.append(self.processFanXingResult(self.QIDUI))
            """碰碰胡 1番"""
            if self.__tile_pattern_checker.isPengpenghu(pattern):
                eachWinnerResultsByPattern.append(self.processFanXingResult(self.PENGPENGHU)) 

            bestWinnerResult = []
            maxScore = 0
            for result in eachWinnerResultsByPattern:
                tempResult = []
                tempResult.append(result)
                calctempResult = []
                calctempResult.extend(tempResult)
                tempScore = self.getScoreByResults(calctempResult)
                if tempScore > maxScore:
                    maxScore = tempScore
                    bestWinnerResult = tempResult

            # 计算当前牌型的赢牌奖励分数，选取最大值的牌型
            calceachWinnerResultsByPattern = []
            #calceachWinnerResultsByPattern.extend(winnerResults)
            calceachWinnerResultsByPattern.extend(bestWinnerResult)
            tempScore = self.getScoreByResults(calceachWinnerResultsByPattern)
            if tempScore > maxPatternScore:
                # 分数相同就不管了
                maxPatternScore = tempScore
                bestWinnerResultsByPattern = calceachWinnerResultsByPattern
        winnerResults.extend(bestWinnerResultsByPattern)
        ftlog.info('MLuosihuOneResult.getWinnerResults xuezhan winnerResults=', winnerResults)
        return winnerResults

    def getLooserResults(self,winSeatId,seatId):
        """和牌时，特定人做过特定操作，只对这个人生效"""
        looserResults = []
        # if self.piaoProcessor.isPiao and self.piaoProcessor.piaoPoints[seatId]:
        #     looserResults.append({'name':'加'+str(self.piaoProcessor.piaoPoints[seatId])+'漂', "index":0, "score":0, 'fanSymbol':''})
        # """明牌输"""
        # if self.isDuiLiangDuiFan(winSeatId,seatId):
        #     looserResults.append(self.processFanXingResult(self.DUILIANGDUIFAN))
        # elif self.isMingshu(winSeatId,seatId):
        #     looserResults.append(self.processFanXingResult(self.MINGSHU))
        # ftlog.info('MLuosihuOneResult.getLooserResults looserResults=', looserResults)
        return looserResults

    def getPaoResults(self):
        """和牌时，计算放炮的人对自身的影响"""
        paoResults = []
        # """海底炮"""
        # if self.__tile_pattern_checker.isHaidipao():
        #     paoResults.append(self.processFanXingResult(self.HAIDIPAO))
        """杠上炮"""
        if self.__tile_pattern_checker.isGangshangpao():
            if self.playMode == 'luosihu-xuezhan':
		maxFan = self.tableConfig.get(MTDefine.MAX_FAN, 0)	
                self.fanXing[self.GANGSHANGPAO]["index"] = maxFan
                paoResults.append(self.processFanXingResult(self.GANGSHANGPAO))
            elif self.playMode == 'luosihu-luosihu':
		if self.tableConfig.get(MTDefine.GANGSHANGPAO, 0):
		    paoResults.append(self.processFanXingResult(self.GANGSHANGPAO))
	    else: 
            	paoResults.append(self.processFanXingResult(self.GANGSHANGPAO))

        ftlog.info('MLuosihuOneResult.getPaoResults paoResults=', paoResults)
        return paoResults

    def processFanXingResult(self, fanSymbol, scoreTimes = 0 ,indexTimes = 1):
        res = {"name":'', "index":0, "score":0, 'fanSymbol':''}
        if self.fanXing[fanSymbol]:
            if self.fanXing[fanSymbol]["name"]:
                res['name'] = self.fanXing[fanSymbol]["name"]
            if self.fanXing[fanSymbol].has_key("index"):
                # 三种番型默认使用当前文件的配置，但如果前端提交了配置，则使用前端提交的配置
                #scoreIndex = self.tableConfig.get(MTDefine.FAN_LIST, [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0])
                #if fanSymbol == self.PENGPENGHU:
                #    res['index'] = scoreIndex.index(self.tableConfig.get(MTDefine.PENGPENGHU_FAN, scoreIndex[self.fanXing[fanSymbol]["index"]]))
                    # if self.__shouzhuayi_result:
                    #     # 碰碰胡后算，当手抓一已经存在的时候，碰碰胡减少2倍番数
                    #     res['index'] -= 1
                # elif fanSymbol == self.LUOSIHU:
                #     res['index'] = scoreIndex.index(self.tableConfig.get(MTDefine.LUOSIHU_FAN, scoreIndex[self.fanXing[fanSymbol]["index"]]))
                #elif fanSymbol == self.GANGKAI:
                #    res['index'] = scoreIndex.index(self.tableConfig.get(MTDefine.GANGSHANGHUA_FAN, scoreIndex[self.fanXing[fanSymbol]["index"]]))
                #else:
                res['index'] = self.fanXing[fanSymbol]["index"] * indexTimes
            if self.fanXing[fanSymbol].has_key("addScore"):
                res['score'] += self.fanXing[fanSymbol]["addScore"]
            if self.fanXing[fanSymbol].has_key("multiplyScore"):
                res['score'] += self.fanXing[fanSymbol]["multiplyScore"] * scoreTimes
            res['fanSymbol'] = fanSymbol
        return res

    def getScoreByResults(self, results, maxFan=0):
        index = 0
        score = 0
        for result in results:
            index += result['index']
            score += result['score']
        scoreIndex = self.tableConfig.get(MTDefine.FAN_LIST, [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0])
        ftlog.info('MLuosihuOneResult.getScoreByResults scoreIndex:', scoreIndex)
        if len(scoreIndex) <= index:
            # 如果超出最大番型的定义，按照len-1计算，防止超出边界
            ftlog.info('MLuosihuOneResult.getScoreByResults exceed fan_list in MTDefine, index=', index)
            index = len(scoreIndex) - 1
        fan = scoreIndex[index]
        if maxFan:
            # maxFan不为0时，限制最大番数。算最大番型时，不要传递此参数，要么就算不出来了
            if fan > maxFan:
                fan = maxFan
        finalScore = fan + score
        ftlog.info('MLuosihuOneResult.getScoreByResults score=', finalScore,' fan=',fan,' index=',index,' result=',results)
        return finalScore

    def getFanByResults(self, results, maxFan=0):
        index = 0
        for result in results:
            index += result['index']
        ftlog.info('MLuosihuOneResult.getFanByResults fan=', index)
        return index

    def getFanPatternListByResults(self, results):
        fanIndex = self.tableConfig.get(MTDefine.FAN_LIST, [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0])
        fanPatternList = []
        names = []
        for result in results:
            ftlog.info('MLuosihuOneResult.getFanByResults result=', result)
            # if result['fanSymbol'] in [self.PAO, self.QIA, self.MO, self.BA]:
            #     # 硬编码，因为目前前端合并一个"跑恰摸八"显示
            #     # 跑恰摸八不算番，只算分
            #     name = result['name']
            #     fan = [result['name']+str(result['score']),"算分"]
            # else:
            name = result['name']
            if result['index']:
		if result['index'] >= len(fanIndex):
		    result['index'] = len(fanIndex)-1
                fan = [result['name'], str(fanIndex[result['index']])+"番"]
            else:
                fan = [result['name'], "算分"]

            if name not in names:
                # 排重
                names.append(name)
                fanPatternList.append(fan)

        ftlog.info('MLuosihuOneResult.getFanPatternListByResults fanPatternList=', fanPatternList)
        return fanPatternList

    def getMaScore(self):
        lstInfo = self.tableTileMgr.getLastSpecialTiles()
        maScore = 0
        # if lstInfo and lstInfo['ma_tile']:
        #     if lstInfo['ma_tile'] in [MTile.TILE_HONG_ZHONG, MTile.TILE_FA_CAI, MTile.TILE_BAI_BAN]:
        #         maScore = 10
        #     elif lstInfo['ma_tile'] > 10 and lstInfo['ma_tile'] < 30:
        #         # 马牌仅能出现筒、条
        #         maScore = lstInfo['ma_tile'] % 10
        # ftlog.info('MLuosihuOneResult.getMaScoreCount maScoreCount: ', maScore)
        return maScore

    def getWinnerGen(self):
        """luosihu-xuezhan中的根计算"""
        #只要你手上有4个一样的，哪怕是碰了之后自己摸的加杠，或者手上有4张一样的牌，没有杠等等都算一番，你有2根就是2番，*4
        #杠牌个数+手中可暗杠个数
        winnerGen = 0
        if self.playMode != 'luosihu-ctxuezhan':
            return False,winnerGen        
        handTiles = self.playerAllTiles[self.winSeatId][MHand.TYPE_HAND]
        tileArr = MTile.changeTilesToValueArr(handTiles)
        for tile in range(MTile.TILE_MAX_VALUE):
            if tileArr[tile] == 4:
                winnerGen += 1
        gangTiles = self.playerAllTiles[self.winSeatId][MHand.TYPE_GANG]
        winnerGen += len(gangTiles)
        pengTiles = self.playerAllTiles[self.winSeatId][MHand.TYPE_PENG]
        for pengTile in pengTiles:
            if pengTile[0] in handTiles:
                winnerGen = winnerGen + 1
        if winnerGen > 0:
            return True,winnerGen
        else:
            return False,winnerGen
    def isShisanyao(self):
        """特殊牌型十三幺的胡牌判断"""
        #十风和十三幺都是必须从开局开始连出,并且不能吃碰杠
        dropTiles = self.tableTileMgr.dropTiles[self.winSeatId]
        nowTiles = self.playerAllTiles[self.winSeatId]

        if len(dropTiles) <= 0:
            return False
        else:
            if len(nowTiles[MHand.TYPE_CHI]) > 0 or len(nowTiles[MHand.TYPE_PENG]) > 0 or len(nowTiles[MHand.TYPE_GANG]) > 0:
                return False
            if not self.isYaopai(dropTiles[0]):
                return False
            count = 0
            for tempTile in dropTiles:
                if self.isYaopai(tempTile):
                    count += 1
                else:
                    count = 0
                    break
            if count >= 13:
                return True        
        
        return False
    
    def isYaopai(self, tile):
        """检查满足十三幺的牌型"""
        if tile >= MTile.TILE_DONG_FENG and tile <= MTile.TILE_BAI_BAN:
            return True
        if tile%10 == 1 or tile %10 == 9:
            return True
        return False

    def isTianHu(self):
        """tianHu:发完牌，庄家胡牌，可以杠"""

        if self.playMode == 'luosihu-luosihu':
            return False
        elif self.playMode == 'luosihu-ctxuezhan':
            if self.tableConfig.get(MTDefine.TIAN_HU, 0) != 1:
                return False
	ftlog.debug('isTianHu self.playMode=',self.playMode)	

        nowTiles = self.playerAllTiles[self.winSeatId]
        if len(nowTiles[MHand.TYPE_PENG]) != 0:
            return False

        if len(nowTiles[MHand.TYPE_GANG]) != 0:
            return False

        # 等于庄家id 并且自己没有打过牌
        if self.winSeatId == self.bankerSeatId and len(self.tableTileMgr.dropTiles[self.winSeatId]) == 0:
	    ftlog.debug('isTianHu self.playMode=2',self.playMode)
            return True
	ftlog.debug('isTianHu self.playMode=3',self.playMode)
        return False

    def isDiHu(self):
        """diHu:发完牌，庄家打出的第一张闲牌"""

        if self.playMode == 'luosihu-luosihu':
            return False
        elif self.playMode == 'luosihu-ctxuezhan':
            if self.tableConfig.get(MTDefine.DI_HU, 0) != 1:
                return False

        nowTiles = self.playerAllTiles[self.winSeatId]
	ftlog.debug('MLuosihuOneResult isDihu 1')
        if len(nowTiles[MHand.TYPE_PENG]) != 0 or len(nowTiles[MHand.TYPE_GANG]) != 0:
            return False
	ftlog.debug('MLuosihuOneResult isDihu 2') 
        dropCount = 0
        for i in range(self.playerCount):
            dropCount += len(self.tableTileMgr.dropTiles[i])

        # 所有人只打了一张牌 并且自己没有摸牌
        if dropCount == 1 and len(self.tableTileMgr.addTiles[self.winSeatId]) == 0:
            return True
	ftlog.debug('MLuosihuOneResult isDihu 3',dropCount,len(self.tableTileMgr.addTiles[self.winSeatId])) 
        return False
 
    def isJinGouDiao(self,isPengPeng):
        """金钩钓: 碰碰，且单吊将
        """
        if not isPengPeng:
            return False
	ftlog.debug('MLuosihuOneResult.getWinnerResults jingoudiao 4')
        # 手牌只剩将对
        nowTiles = self.playerAllTiles[self.winSeatId]
        handTiles = nowTiles[MHand.TYPE_HAND]
        if len(handTiles) == 2 and handTiles[0] == handTiles[1]:
            return True
	
	if len(handTiles) < 2:
	    return True
	
	ftlog.debug('MLuosihuOneResult.getWinnerResults jingoudiao 5',len(handTiles),handTiles[0])
        return False

    def getGangCount(self):
        """杠"""
        gangTiles = self.playerAllTiles[self.winSeatId][MHand.TYPE_GANG]
        return len(gangTiles)

    def isJiangDui(self):
        """
        将对:在【对对胡】牌型中，都是由2,5,8组成的刻字喝将牌
        """
        jiang258 = [2,5,8,12,15,18,22,25,28]
        handTiles = self.playerAllTiles[self.winSeatId][MHand.TYPE_HAND]
        chiTiles  = self.playerAllTiles[self.winSeatId][MHand.TYPE_CHI]
        pengTiles = self.playerAllTiles[self.winSeatId][MHand.TYPE_PENG]#[[4, 4, 4]]
        gangTiles = self.playerAllTiles[self.winSeatId][MHand.TYPE_GANG] #'gang': [{'pattern': [31, 31, 31, 31], 'style': True, 'actionID': 11}]

        for tile in handTiles:
            if not tile in jiang258:
                return False
        if len(chiTiles) > 0:
                return False
        for tilePatten in pengTiles:
            if not tilePatten[0] in jiang258:
                return False
        for tile in gangTiles:
            if not tile['pattern'][0] in jiang258:
                return False

        ftlog.debug('MLuosihuOneResult.isJiangDui result: True')
        return True

    def isYaoJiu(self,patterns):
        """
        幺九:每副顺子，刻字，将牌都包含1或9
        """
        yaojiu = [1,9,11,19,21,29]

        chiTiles  = self.playerAllTiles[self.winSeatId][MHand.TYPE_CHI]
        pengTiles = self.playerAllTiles[self.winSeatId][MHand.TYPE_PENG]
        gangTiles = self.playerAllTiles[self.winSeatId][MHand.TYPE_GANG]

        for tilePatten in pengTiles:
            if not tilePatten[0] in yaojiu:
                return False
        for tile in gangTiles:
            if not tile['pattern'][0] in yaojiu:
                return False
        if len(chiTiles) > 0:
            return False
	ftlog.debug('MLuosihuOneResult isYaojiu 1')
        for pattern in patterns:
            isyaojiu = False
            for tile in pattern:
                if tile in yaojiu:
                    isyaojiu = True
            if isyaojiu != True:
                return False 
	ftlog.debug('MLuosihuOneResult isYaojiu 2')
        return True

    def isHaidilao(self):
        """
        海底捞：最后一张牌自摸和牌
        """  
        if self.lastSeatId == self.winSeatId:
            if self.tableTileMgr and self.tableTileMgr.getTilesLeftCount() == 0:
                ftlog.debug('MTilePatternChecker.isHaidilao result: True')
                return True
        
        ftlog.debug('MTilePatternChecker.isHaidilao result: False')
        return False

    def checkDaDiaoChe(self):
        """检查大吊车：只剩一张牌单吊，自摸
        """
        tiles = self.playerAllTiles[self.winSeatId]
        return len(tiles[MHand.TYPE_HAND]) == 1

    def isDuanYaoJiu(self):
        """
        断幺九:每副顺子，刻字，将牌都不包含1或9
        """
        playerAllTiles = MHand.copyAllTilesToList(self.playerAllTiles[self.winSeatId])
        yaoJiuCount = 0
        for tile in playerAllTiles:
            if MTile.getColor(tile) == MTile.TILE_FENG or tile%10 == 1 or tile%10 == 9:
                yaoJiuCount += 1

        return yaoJiuCount == 0

    def checkMenQing(self):
        """检查门清，没有碰和明杠，点炮也算门清
        """
        tiles = self.playerAllTiles[self.winSeatId]
        # 没有碰
        if len(tiles[MHand.TYPE_PENG]) > 0:
            return False

        # 没有明杠
        for gang in tiles[MHand.TYPE_GANG]:
            if gang['style'] == MPlayerTileGang.MING_GANG:
                return False

        return True

    def isMinghu(self,seatId):
        """
        明牌胡：亮倒后和牌
        """ 
        # if self.__player_ting_liang[seatId] == True:
        #     ftlog.info('MLuosihuOneResult.isMinghu result: True')
        #     return True
        # ftlog.info('MLuosihuOneResult.isMinghu result: False')
        return False

    def isMingshu(self, winSeatId,seatId):
        """
        明牌输：亮倒后输牌
        """ 
        # if self.isMinghu(winSeatId) == False and self.__player_ting_liang[seatId] == True:
        #     # 当赢家是明牌的情况下，输家即使也明牌了，不再额外罚分
        #     ftlog.info('MLuosihuOneResult.isMingshu result: True')
        #     return True
        # ftlog.info('MLuosihuOneResult.isMingshu result: False')
        return False
    
    def isDuiLiangDuiFan(self,winSeatId,shuSeatId):
        if not self.tableConfig.get(MTDefine.DUILIANGDUIFAN,0):
            return False
        # if self.__player_ting_liang[winSeatId] == True and self.__player_ting_liang[shuSeatId] == True:
        #     return True
        
    def setTilePatternChecker4Test(self, tilePatternChecker):
        # 仅用于测试
        self.__tile_pattern_checker = tilePatternChecker

    def setPlayerTingLiang4Test(self, tingLiangState):
        # 仅用于测试
        # self.__player_ting_liang = tingLiangState
	ftlog.debug('setPlayerTingLiang4Test')

    def setWinPatterns4Test(self, winPatterns):
        # 仅用于测试
        self.__win_patterns = winPatterns


if __name__ == "__main__":
    result = MLuosihuOneResult()
    tilePatternChecker = MTilePatternCheckerFactory.getTilePatternChecker(MPlayMode.LUOSIHU)
    tableTileMgr = MTableTileFactory.getTableTileMgr(3, 'luosihu', 1)

    # 清一色海底捞，8分, 0号明牌输
    tableConfig = {'fan_list': [1, 2, 4, 8, 16, 32, 64, 128, 256, 512, 1024]}
    tableTileMgr.tileTestMgr.setTiles([])
    tilePatternChecker.setPlayerHandTilesWithHu([[],[16,16,15,16,17,14,15,16,11,12,13],[]])
    tilePatternChecker.setPlayerAllTiles([{},{MHand.TYPE_PENG:[], MHand.TYPE_GANG:[]},{}])
    tilePatternChecker.setPlayerAllTilesArr([[],[16,16,15,16,17,14,15,16,11,12,13],[]])
    tilePatternChecker.setLastSeatId(1)
    tilePatternChecker.setWinSeatId(1)
    tilePatternChecker.setWinTile(11)
    tilePatternChecker.setTableConfig(tableConfig)
    tilePatternChecker.setTableTileMgr(tableTileMgr.tileTestMgr)
    result.setTilePatternChecker4Test(tilePatternChecker)
    result.setWinPatterns4Test([[[[1,1]]],[[[16, 16], [15, 16, 17], [14, 15, 16], [11, 12, 13]]]])
    result.setLastSeatId(1)
    result.setWinSeatId(1)
    result.setWinSeats([1])
    result.setPlayerCount(3)
    result.setWinTile(11)
    result.setPlayerTingLiang4Test([True, False, False])
    result.setTableConfig(tableConfig)
    result.setTableTileMgr(tableTileMgr.tileTestMgr)
    assert 8 == result.getScoreByResults(result.getWinnerResults(1))
    result.calcWin([1],[[],[16,16,15,16,17,14,15,16,11,12,13],[]])
    ftlog.info(result.results)
    assert result.results[result.KEY_SCORE] == [-16, 24, -8]

    #清一色手抓一，16分
    tableConfig = {'fan_list': [1, 2, 4, 8, 16, 32, 64, 128, 256, 512, 1024]}
    tableTileMgr.tileTestMgr.setTiles([20,21,22])
    tilePatternChecker.setPlayerHandTilesWithHu([[],[11, 11],[]])
    tilePatternChecker.setPlayerAllTiles([{},{MHand.TYPE_PENG:[], MHand.TYPE_GANG:[]},{}])
    tilePatternChecker.setPlayerAllTilesArr([[],[16,16,15,16,17,14,15,16,11,12,13],[]])
    tilePatternChecker.setLastSeatId(1)
    tilePatternChecker.setWinSeatId(1)
    tilePatternChecker.setWinTile(11)
    tilePatternChecker.setTableConfig(tableConfig)
    tilePatternChecker.setTableTileMgr(tableTileMgr.tileTestMgr)
    result.setTilePatternChecker4Test(tilePatternChecker)
    result.setWinPatterns4Test([[[[1,1]]],[[[11, 11], [13, 13, 13], [14, 14, 14], [15, 15, 15]]]])
    result.setLastSeatId(1)
    result.setWinSeatId(1)
    result.setWinSeats([1])
    result.setPlayerCount(3)
    result.setWinTile(11)
    result.setPlayerTingLiang4Test([False, False, False])
    result.setTableConfig(tableConfig)
    result.setTableTileMgr(tableTileMgr.tileTestMgr)
    assert 16 == result.getScoreByResults(result.getWinnerResults(1))
        
    result.calcWin([1],[[],[16,16,15,16,17,14,15,16,11,12,13],[]])
    ftlog.info(result.results)
    assert result.results[result.KEY_SCORE] == [-16, 32, -16]
    assert result.results[result.KEY_WIN_MODE] == [-2, 0, -2]

    #放杠2倍
    #result.setLastSeatId(2)
    #result.setWinSeatId(1)
    #result.setPlayerCount(3)
    #result.setStyle(MPlayerTileGang.MING_GANG)
    #result.calcGang()
    #ftlog.info(result.results)
    #assert result.results[result.KEY_SCORE] == [0, 2, -2]

    #蓄杠2倍
    #result.setLastSeatId(1)
    #result.setWinSeatId(1)
    #result.setPlayerCount(3)
    #result.setStyle(MPlayerTileGang.MING_GANG)
    #result.calcGang()
    #ftlog.info(result.results)
    #assert result.results[result.KEY_SCORE] == [-1, 2, -1]
