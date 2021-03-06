# -*- coding=utf-8
'''
Created on 2017年6月6日
winRule
@author: youjun
'''
from majiang2.win_rule.win_rule import MWinRule
from majiang2.ai.win import MWin
from majiang2.player.hand.hand import MHand
from freetime.util import log as ftlog
from majiang2.table.table_config_define import MTDefine
from majiang2.tile.tile import MTile
import copy
class MWinRuleQueshou(MWinRule):

    MODE_ZIMO = 1
    MODE_XIAOPINGHU = 2
    MODE_DAPINGHU = 3
    MODE_QIANGGANGHU = 4
    MODE_QINGYISE = 5
    MODE_HUNYISE = 6
    MODE_JINKAN = 7
    MODE_JINQUE = 8

    def __init__(self):
        super(MWinRuleQueshou, self).__init__()
    
    def isHu(self, tiles, tile, isTing, getTileType, magicTiles = [], tingNodes = [], curSeatId = 0, winSeatId = 0, actionID = 0, isGangKai = False,isForHu = True):
	#ftlog.debug('MWinRuleQueshou.isHu magicTiles=',magicTiles)

	result, pattern= MWin.isHu(tiles[MHand.TYPE_HAND], magicTiles)
	if not result:
            return False, [],0
	winMode = 0
	if not len(magicTiles):
	    return False, [],0
	if isTing and isForHu and len(magicTiles) > 0:
	    if tile != magicTiles[0]:
		return False,[],0
	    if getTileType != MWinRule.WIN_BY_MYSELF:
	        return False,[],0

        if self.tableConfig.get(MTDefine.QINGHUNYISE, 0):
            #ftlog.debug('isHu isqinghunyise called')
            if self.isHunyise(tiles,magicTiles):
                winMode = self.MODE_HUNYISE
		return result, pattern,winMode	
            if self.isQingyise(tiles):
                winMode = self.MODE_QINGYISE 
		return result, pattern,winMode

        if 1:	#self.tableConfig.get(MTDefine.DANDIAOSHENGJIN, 0):
            handTiles = copy.deepcopy(tiles[MHand.TYPE_HAND])
            handTiles.remove(tile)
            if len(handTiles) == 1 and handTiles[0] == magicTiles[0]:
                if getTileType != MWinRule.WIN_BY_MYSELF:
                    return False,[],0
	handTiles = copy.deepcopy(tiles[MHand.TYPE_HAND])
        if result and getTileType != MWinRule.WIN_BY_MYSELF:
            if tile == magicTiles[0]:
                return False,[],0 
            if self.canJinQue(magicTiles[0],pattern,handTiles,tile):
		handTiles = copy.deepcopy(tiles[MHand.TYPE_HAND])
		if not self.isJinQue(magicTiles[0],pattern,handTiles):
                    return False,[],0
	
	handTiles = copy.deepcopy(tiles[MHand.TYPE_HAND]) 
	if self.isYouJin(magicTiles[0],pattern,handTiles,tile):
	    if getTileType != MWinRule.WIN_BY_MYSELF:
		return False,[],0

        if getTileType == MWinRule.WIN_BY_MYSELF:
            winMode = self.MODE_ZIMO

        if self.isXiaoPingHu(winSeatId):
            winMode = self.MODE_XIAOPINGHU

        if self.isDaPingHu(winSeatId):
            winMode = self.MODE_DAPINGHU
	handTiles = copy.deepcopy(tiles[MHand.TYPE_HAND])

        if len(magicTiles) > 0 and self.isJinQue(magicTiles[0],pattern,handTiles):	#(magicTiles[0],pattern):
            winMode = self.MODE_JINQUE

        if isTing and getTileType == MWinRule.WIN_BY_MYSELF and len(magicTiles) > 0 and tile == magicTiles[0]:
            winMode = self.MODE_JINKAN
	'''
        if self.tableConfig.get(MTDefine.QINGHUNYISE, 0):
	    #ftlog.debug('isHu isqinghunyise called')
            if self.isHunyise(tiles,magicTiles):
                winMode = self.MODE_HUNYISE
            if self.isQingyise(tiles):
                winMode = self.MODE_QINGYISE
	'''
        return result, pattern,winMode

    def isMagicHu(self, tiles, tile, isTing, getTileType, magicTiles = [], tingNodes = [], curSeatId = 0, winSeatId = 0, actionID = 0, isGangKai = False):
        if len(magicTiles) >0:
            # 三金倒
            magicHu,pattern = MWin.isMagicHu(tiles,magicTiles[0],tile)
            #if magicHu and actionID > 1:
            return magicHu


    def getHuPattern(self, tiles, magicTiles = []):
        return MWin.isHu(tiles[MHand.TYPE_HAND], magicTiles)

    def isPassHu(self):
        """是否有过胡规则"""
        return True

    def canJinQue(self,magicTile,pattern,handTiles,tile):
	'''
        magicCount = MTile.getTileCount(magicTile,handTiles)
        if magicCount == 2:
            result, pattern= MWin.isHu(handTiles, [])
	    ftlog.debug('MWinRuleQueshou.canJinQue result, pattern=',result, pattern)
            if result:
                return True
        return False
	'''
        magicCount = MTile.getTileCount(magicTile,handTiles)
        if magicCount == 2:
            if tile in handTiles:
                handTiles.remove(tile)
                handTiles.append(31)
            result, pattern= MWin.isHu(handTiles, [31])
	    ftlog.debug('MWinRuleQueshou.canJinQue result, pattern=',result, pattern,handTiles)
            if result:
                return True

        return False

    def isYouJin(self,magicTile,pattern,handTiles,tile):
        '''
        游金：金做将对
        游金不胡点炮
	
	ftlog.debug('MWinRuleQueshou.isYouJin pattern,handTiles,tile',pattern,handTiles,tile)
        for p in pattern:
            if len(p) == 2:
                if magicTile in p:
                    p.remove(magicTile)
                    if p[0] == tile:
                        return True
	'''
	magicCount = MTile.getTileCount(magicTile,handTiles)
        if magicCount == 1:
            if tile in handTiles:
                handTiles.remove(tile)
                handTiles.append(31)
            result, pattern= MWin.isHu(handTiles, [magicTile])
            #ftlog.debug('MWinRuleQueshou.canJinQue result, pattern=',result, pattern,handTiles)
            if result:
                return True
	return False


    def isJinQue(self,magicTile,pattern,handTiles):
        """
        金雀：金做将对
        """ 
	magicCount = MTile.getTileCount(magicTile,handTiles) 
	if magicCount != 2:
	    return False
        for p in pattern:
            for oneTile in p:
                if oneTile in handTiles:
                    handTiles.remove(oneTile)
        if len(handTiles) == 2 and handTiles[0] == handTiles[1] and handTiles[0] == magicTile:
            return True
        return False

    def isDaPingHu(self,winSeatId):
	
        flowerTiles = self.tableTileMgr.players[winSeatId].flowers
        gangTiles = self.tableTileMgr.players[winSeatId].copyGangArray()
        if len(flowerTiles) == 0 and len(gangTiles) == 0:
            return True
	
        return False

    def isXiaoPingHu(self,winSeatId):
	'''	
        flowerTiles = self.tableTileMgr.players[winSeatId].flowers

        if len(flowerTiles) == 1:
            return True
	
        return False
	'''
        player = self.tableTileMgr.players[winSeatId]
        flowerTiles = player.flowers
        gangList = player.copyGangArray()
        
        angangScore = 0
        minggangScore = 0
        for gang in gangList:
            if gang['style'] == 0:  # 暗杠
                angangScore += 2
            else:
                minggangScore += 1

        score = len(flowerTiles) + angangScore + minggangScore
        if score == 1:
            return True
        return False

    def isQingyise(self, tiles):
        """
        清一色：由同一门花色（筒子或条子）组成的和牌牌型
        """
        tileArr = MTile.changeTilesToValueArr(MHand.copyAllTilesToListButHu(tiles))
        colors = MTile.getColorCount(tileArr)
        #ftlog.debug('MWinRuleQueshou.isQingyise tileArr=',tileArr,colors)
	return colors == 1

    def isHunyise(self, tiles, magicTiles):
	if not len(magicTiles):
	    return False
	magicTile = magicTiles[0]
	magicCount = 0
        allTiles = MHand.copyAllTilesToListButHu(tiles)
        allTileArr = MTile.changeTilesToValueArr(allTiles)
        allColors = MTile.getColorCount(allTileArr)
        for tile in allTiles:
	    if tile == magicTile:
		magicCount = magicCount + 1

        for i in range(magicCount):
            allTiles.remove(magicTile)

        tileArr = MTile.changeTilesToValueArr(allTiles)
        colors = MTile.getColorCount(tileArr)
	#ftlog.debug('MWinRuleQueshou.isHunyise allColors colors=',allColors,colors,magicCount,allTiles)
        if allColors == 2 and colors == 1:
            return True
        return False 

