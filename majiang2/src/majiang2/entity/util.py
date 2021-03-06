# -*- coding=utf-8 -*-
'''
Created on 2015年10月17日
@author: liaoxx
'''
import functools
from freetime.util import log as ftlog
from hall.entity.todotask import TodoTaskHelper, TodoTaskShowInfo, TodoTaskPopTip
from poker.entity.dao import sessiondata,userdata
from poker.entity.biz.message import message
from poker.util import strutil
from majiang2.entity import majiang_conf
from poker.protocol import router 
from hall.entity import hallshare, hallled
from hall.entity.hallconf import HALL_GAMEID
import json
import base64
import collections

class Util(object):
    @classmethod
    def dict2list(cls, d):
        l = []
        if isinstance(d, dict):
            for k, v in d.iteritems():
                l.append(k)
                l.append(v)
        return l
    
    @classmethod
    def dict_sort(cls, d, ol):
        """sort dict by ol
        """
        if len(ol) <= 0:
            return d

        if len(d.keys()) >= len(ol):
            s_list, l_list = ol, d.keys()
        else:
            s_list, l_list = d.keys(), ol

        diff_l = cls.list_diff(s_list, l_list)

        nol = ol[:]
        nol.extend(diff_l)
        if sorted(d.keys()) == sorted(nol):
            sd = collections.OrderedDict()
            for k in nol:
                sd[k] = d.get(k)
            return sd

        return d

    @classmethod
    def list2dict(cls, l):
        d = {}
        if isinstance(l, list):
            length = len(l)
            while length > 1:
                d[l[length-2]] = l[length-1]
                length -= 2
        return d

    @classmethod
    def list_merge(cls, l1, l2):
        l = []
        for i, j in zip(l1, l2):
            l.append(i)
            l.append(j)
        return l

    @classmethod
    def check_msg_result(cls, msg):
        if not msg._ht.has_key('result'):
            msg._ht['result'] = {}
            
    @classmethod
    def sendShowInfoTodoTask(cls, uid, gid, msg):
        info = TodoTaskShowInfo(msg, True)
        TodoTaskHelper.sendTodoTask(gid, uid, info)    

    @classmethod
    def getClientVerAndDeviceType(cls, clientId):
        infos = clientId.split('_')
        if len(infos) > 2:
            try:
                clientVer = float(infos[1])
                deviceType = infos[0].lower()
                return clientVer, deviceType
            except:
                pass
        return 0, ''            

    @classmethod
    def getClientId(self, uid):
        if uid < 10000:
            clientId = "IOS_3.711_tyGuest.appStore.0-hall7.test.kuaile"
        else:
            clientId = sessiondata.getClientId(uid)
        return  clientId
    
    @classmethod
    def getClientIdVer(self, uid):
        if uid < 10000:
            clientId = 3.7
        else:
            clientId = sessiondata.getClientIdVer(uid)
        return  clientId
    
    @classmethod
    def list_diff(cls, short_list, long_list):
        '''获取list差集
        '''
        l_list = strutil.cloneData(long_list)
        for l in short_list:
            if l in l_list:
                l_list.remove(l)
        return l_list
    
    @classmethod
    def list_intersection(cls, a_list, b_list):
        '''获取list交集
        '''
        return [v for v in a_list if v in b_list]
    
    @classmethod
    def list_union(cls, a_list, b_list):
        '''不去重复元素的list并集
        '''
        return a_list + [v for v in b_list if v not in a_list]
        
def sendPrivateMessage(userId, msg):
    """ 发送个人消息
    """
    if not isinstance(msg, unicode):
        msg = unicode(msg)
    message.sendPrivate(9999, userId, 0, msg)

def safemethod(method):
    """ 方法装饰，被装饰函数不会将异常继续抛出去
    """
    @functools.wraps(method)
    def safetyCall(*args, **kwargs):
        try:
            return method(*args, **kwargs)
        except:
            ftlog.exception()
    return safetyCall


def sendPopTipMsg(userId, msg):
    task = TodoTaskPopTip(msg)
    task.setParam('duration', 3)
    mo = TodoTaskHelper.makeTodoTaskMsg(HALL_GAMEID, userId, task)
    router.sendToUser(mo, userId) 

def sendTableInviteShareTodoTask(userId, gameId, tableNo, playMode, cardCount, contentStr):
    '''牌桌上邀请处理
    '''
    shareId = hallshare.getShareId('mj_invite_play_share', userId, gameId)
    if shareId:
        share =  hallshare.findShare(shareId)
        if not share:
            return
        
        retDesc = ''
        play_mode_dict = majiang_conf.get_room_other_config(gameId).get('playmode_desc_map', {})

        if gameId == 715:
            retDesc = contentStr;
        else:
            retDesc += play_mode_dict.get(playMode,'') if playMode else ''
            retDesc += contentStr
        ftlog.debug('sendTableInviteShareTodoTask last retDesc:', retDesc)
        share.setDesc(retDesc)
        
        if gameId == 715:
            title = play_mode_dict.get(playMode,'') if playMode else ''
            title += ' - 房号:' + tableNo
        else:
            title = share.title.getValue(userId, gameId)
            title = '房间号：' + tableNo + '，' + title
        share.setTitle(title)
        ftlog.debug('sendTableInviteShareTodoTask newTitle:', title)
        
        url = share.url.getValue(userId, gameId)
        url += "?ftId=" + tableNo
        url += "?from=magicWindow"
        eParams = {}
        eParams['action'] = 'hall_enter_friend_table_direct'
        fParam = {}
        fParam['ftId'] = tableNo
        eParams['params'] = fParam
        paramStr = json.dumps(eParams)
        base64Str = base64.b64encode(paramStr)
        from urllib import quote
        url += "&enterParams=" + quote(base64Str)
        share.setUrl(url)
        ftlog.debug('sendTableInviteShareTodoTask newUrl:', url
                    , ' ftId:', tableNo
                    , ' paramStr:', paramStr
                    , ' base64Str:', base64Str)
        
        todotask = share.buildTodotask(gameId, userId, 'mj_invite_play_share')
        mo = TodoTaskHelper.makeTodoTaskMsg(gameId, userId, todotask)
        router.sendToUser(mo, userId)

def send_led(cls, gameId, msg):
    '''系统led'''
    hallled.sendLed(gameId, msg, 0)

def isUserEnabledGps(userId):
    """用户是否开启了gps, 有geo坐标数据就认为是已经开启
    """
    lat1, lon1 = userdata.getAttrs(userId, ["geoLat", "geoLon"])
    ftlog.debug("util.isUserEnabledGps userId", userId, "lat", lat1, "lon1", lon1)
    return lat1 and lon1

def getGeoDistance(userId1, userId2):
    '''计算两个玩家距离 单位：米
       无法测量时返回-1
    '''
    lat1, lon1 = userdata.getAttrs(userId1, ["geoLat", "geoLon"])
    lat2, lon2 = userdata.getAttrs(userId2, ["geoLat", "geoLon"])
    if not lat1 or not lat2:
        return -1

    if abs(lat1) < 1e-100 or abs(lat2) < 1e-100:
        return -1

    geoint1 = geohash.encode(lat1, lon1)
    geoint2 = geohash.encode(lat2, lon2)

    dist = -1
    try:
        dist = geohash.get_distance(geoint1, geoint2)
    except Exception, e:
        ftlog.error("getGeoDistance, |lat1, lon1, lat2, lon2, geoint1, geoint2:",
                    lat1, lon1, lat2, lon2, geoint1, geoint2, e)
    return dist


if __name__ == "__main__":
    di = {"wanFa": 1, "cardCount": 2}
    d2 = Util.dict_sort(di, [])
    print d2
