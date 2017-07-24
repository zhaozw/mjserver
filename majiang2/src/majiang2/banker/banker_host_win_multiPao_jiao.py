# -*- coding=utf-8
'''
Created on 2017.05.17
庄家规则
@author: youjun
'''
from majiang2.banker.banker import MBanker
import random
from freetime.util import log as ftlog

class MBankerHostWinMultiPaoJiao(MBanker):
    """
    首局房主坐庄,如果一炮多响时点炮者坐庄,之后第一个胡者接庄,流局有胡者并且不是一炮多响时第一个胡者当庄,没人胡庄不变
    """
    def __init__(self):
        super(MBankerHostWinMultiPaoJiao, self).__init__()

    def getBankerForXueZhan(self,playerCount,isFirst,winLoose,players,winScores):
        
        if isFirst:
            self.banker = 0
            self.no_result_count = 0
            self.remain_count = 0
        else:
            if winLoose:
                banker = self.calcNextBankerForXueZhan(playerCount,players)
                if self.banker == banker:
                    self.banker = banker
                    self.remain_count += 1
                    self.remain_count = 0
                else:
                    self.banker = banker
                    self.remain_count = 0
                    self.remain_count = 0
            else:
                banker = self.calcNextBankerForXueZhanJiao(playerCount,winScores)
                if self.banker == banker:
                    self.banker = banker
                    self.remain_count += 1
                    self.remain_count = 0
                else:
                    self.banker = banker
                    self.remain_count = 0
                    self.remain_count = 0

        return self.banker, self.remain_count, self.no_result_count
    
    def calcNextBankerForXueZhan(self,playerCount,players):
        xuezhanRanks = [ 100 for _ in range(playerCount) ]
        for seatId in range(playerCount):
	    ftlog.debug('MBankerHostWinMultiPaoJiao.calcNextBankerForXueZhan xuezhanRanks:',xuezhanRanks,players[seatId].xuezhanRank)
            xuezhanRanks[seatId] = players[seatId].xuezhanRank
        bankerRank = min(xuezhanRanks) 
        for seatId in range(playerCount):
            if players[seatId].xuezhanRank == bankerRank:
                return seatId

    def calcNextBankerForXueZhanJiao(self,playerCount,scores):   
        # 查大叫分最大的为庄     
	bankerScore = max(scores) 
	ftlog.debug('MBankerHostWinMultiPaoJiao.calcNextBankerForXueZhanJiao scores:',scores,bankerScore)	
        if not bankerScore:
            return self.banker
        for seatId in range(playerCount):
            if scores[seatId] == bankerScore:
                return seatId
    	return self.banker
    def getBanker(self, playerCount, isFirst, winLoose, winSeatId, extendInfo = {}):
        """子类必须实现
        参数：
        1）isFirst 是否第一局
        2）winLoose 上局的结果 1分出了胜负 0流局
        3）winSeatId 赢家的座位号，如果第二个参数为0，则本参数为上一局的庄家
        
        # 1.首局房主坐庄,最先胡牌者当庄
        # 2.流局没人和牌者，则大叫玩家做庄
        # 3.没人有叫,则上局庄家继续做庄
        # 4.若出现一炮多响,则炮者当庄
        
        """


        
        """子类必须实现
        参数：
        1）isFirst 是否第一句
        2）winLoose 上局的结果 1分出了胜负 0流局
        3）winSeatId 赢家的座位号，如果第二个参数为0，则本参数为上一局的庄家
        """
        if isFirst:
            # 初始化，随机选庄
            self.banker = 0
            self.no_result_count = 0
            self.remain_count = 0
        else:
            if winLoose == MBanker.ONE_WIN_ONE_LOOSE:
                # 有输赢结果
                if winSeatId == self.banker:
                    # 赢得是庄家
                    self.remain_count += 1
                    self.no_result_count = 0
                else:
                    # 赢得是闲家
                    self.banker = winSeatId
                    self.remain_count = 0
                    self.no_result_count = 0
            elif winLoose == MBanker.MULTI_WIN_ONE_LOOSE:
                self.banker = winSeatId
                self.remain_count = 0
                self.no_result_count = 0
            else:
                # 荒牌，流局，庄家继续，荒牌次数加一，坐庄次数加一
                self.banker = (self.banker + 1) % playerCount
                self.no_result_count = 0
                self.remain_count = 0
        
        ftlog.info('MBankerRandomHuangNextMuiltPao.getBanker playerCount:', playerCount
                   , ' isFirst:', isFirst
                   , ' winLoose:', winLoose
                   , ' winSeatId:', winSeatId
                   , ' banker:', self.banker
                   , ' remainCount:', self.remain_count
                   , ' noResultCount:', self.no_result_count)        
        return self.banker, self.remain_count, self.no_result_count

    def calcNextBanker(self, playerCount, winLoose, winSeatId, extendInfo = {}):
        """ 计算下一个庄家
            只是计算，不是真的设置庄家
            设置庄家请继续使用getBanker接口
        """

        if winLoose == MBanker.ONE_WIN_ONE_LOOSE:
            # 有输赢结果
            if winSeatId == self.banker:
                return self.banker
            else:
                return winSeatId
        elif winLoose == MBanker.MULTI_WIN_ONE_LOOSE:
            return winSeatId
        else:
            return (self.banker + 1) % playerCount
