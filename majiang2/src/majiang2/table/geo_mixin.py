# -*- coding:utf-8 -*-
'''
Created on 13/06/2017

@author: zhaojm
'''

import time
from majiang2.entity import util 
from majiang2.table.friend_table_define import MFTDefine
from freetime.util import log as ftlog


class GEOMixin(object):
    GEO_INTERVAL = 40  # 40s  GEO 检查间隔

    def __init__(self,playerCount,msgProcessor):
        self._last_geo_sent_at = 0  # 最近一次给玩家发送geo的时间
        self._geo_gps = None  # 玩家的gps状态
        self._geo_distances = None  # 玩家之间的物理距离
        self._players = [ None for _ in xrange(playerCount)]
        self._playerCount = playerCount
        self._msg_processor = msgProcessor

    @property
    def player(self):
        return self._players

    def setPlayer(self,players):
        self._players = players

    @property
    def playerCount(self):
        return self._playerCount

    @property
    def msgProcessor(self):
        return self._msg_processor

    def reset(self):
        self._last_geo_sent_at = 0
        self._geo_distances = None
        self._geo_gps =None
        self._players = [None for _ in xrange(self.playerCount)]

    @property
    def tableConfig(self):
        return self._tableConfig

    def setTableConfig(self,config):
        self._tableConfig = config

    def getBroadCastUIDs(self, filter_id = -1):
        """获取待广播的UID集合，不包括filter_id及机器人
        不需要向机器人发送消息
        """
        uids = []
        for player in self.player:
            if player and (not player.isRobot()) and (player.userId != filter_id):
                uids.append(player.userId)
        return uids

    def checkGeo_internal(self):
        """检查geo数据，拆分出新函数_internal，方便写热更
        """
	ftlog.debug("AutoDecide._checkGeo_internal called")
        if self.tableConfig.get(MFTDefine.NEED_GEO, 0):
            # 等待状态中的玩家距离检查
            now = time.time()
            if now - self._last_geo_sent_at > self.GEO_INTERVAL > 0:
                self._last_geo_sent_at = now
                ftlog.debug("AutoDecide._checkGeo_internal...now", now)
                # gps
                gps = [0] * self.playerCount
                for i in xrange(self.playerCount):
                    p1 = self.player[i]
                    if p1 is not None:
                        if util.isUserEnabledGps(p1.userId):
                            gps[i] = 1
                # 设置distances
                distances = {}
                for i in xrange(self.playerCount):
                    for j in xrange(i + 1, self.playerCount):
                        key = '%d-%d' % (i, j)
                        distances[key] = -1
                        if gps[i] and gps[j]:
                            userId1, userId2 = self.player[i].userId, self.player[j].userId
                            distances[key] = util.getGeoDistance(userId1, userId2)
                # 发送geo数据
                self._geo_gps = gps
                self._geo_distances = distances
                self.send_geo_local()

    def send_geo_local(self):
        uids = self.getBroadCastUIDs()
        ftlog.debug("AutoDecide._checkGeo_internal...gps", self._geo_gps, "distances", self._geo_distances, "uids",
                    uids)
        if self._geo_gps and self._geo_distances:
            self.msgProcessor.table_call_geo(self._geo_gps, self._geo_distances, uids)
