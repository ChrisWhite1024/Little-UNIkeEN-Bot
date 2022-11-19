from utils.basicConfigs import ROOT_PATH
from utils.responseImage import *
from utils.basicEvent import send, warning
from typing import Union, Tuple, Any, List
from utils.standardPlugin import StandardPlugin, PluginGroupManager
from utils.basicEvent import getPluginEnabledGroups
from threading import Timer, Semaphore
from resources.api.mddApi import mddUrl, mddHeaders
from datetime import datetime
import os.path

class MddStatus(StandardPlugin):
    monitorSemaphore = Semaphore()
    @staticmethod
    def dumpMddStatus(status: bool):
        exactPath = 'data/mdd.json'
        with open(exactPath, 'w') as f:
            f.write('1' if status else '0')
    @staticmethod
    def loadMddStatus()->bool:
        exactPath = 'data/mdd.json'
        with open(exactPath, 'r') as f:
            return f.read().startswith('1')
    def __init__(self) -> None:
        self.timer = Timer(5, self.mddMonitor)
        if MddStatus.monitorSemaphore.acquire(blocking=False):
            self.timer.start()
        self.exactPath = 'data/mdd.json'
        self.prevStatus = False # false: 暂停营业, true: 营业
        if not os.path.isfile(self.exactPath):
            MddStatus.dumpMddStatus(False)
        else:
            self.prevStatus = MddStatus.loadMddStatus()
    def mddMonitor(self):
        self.timer.cancel()
        self.timer = Timer(60,self.mddMonitor)
        self.timer.start()
        prevStatus = MddStatus.loadMddStatus()
        req = getMddStatus()
        if req == None: return
        try:
            currentStatus = req["data"]["onlineBusinessStatus"]
        except KeyError as e:
            warning('mdd api failed: {}'.format(e))
            return
        if currentStatus != prevStatus:
            MddStatus.dumpMddStatus(currentStatus)
            if currentStatus :
                for group in getPluginEnabledGroups('sjtuinfo'):
                    send(group, '📣交大闵行麦当劳 已▶️开放营业')
            else:
                for group in getPluginEnabledGroups('sjtuinfo'):
                    send(group, '📣交大闵行麦当劳 已⏸️暂停营业')
    def judgeTrigger(self, msg: str, data: Any) -> bool:
        return msg == '-mdd'
    def executeEvent(self, msg: str, data: Any) -> Union[None, str]:
        target = data['group_id'] if data['message_type']=='group' else data['user_id']
        req = getMddStatus()
        if req == None:
            send(target, '获取交大闵行麦当劳状态失败！', data['message_type'])
        try:
            currentStatus = req["data"]["onlineBusinessStatus"]
        except KeyError as e:
            warning("mdd api failed: {}".format(e))
            send(target, '获取交大闵行麦当劳状态失败！', data['message_type'])
            return
        if currentStatus :
            send(target, '交大闵行麦当劳当前状态：\n▶️营业中\n\n%s'%datetime.now().strftime("%Y-%m-%d %H:%M:%S"), data['message_type'])
        else:
            send(target, '交大闵行麦当劳当前状态：\n⏸️暂停营业%s'%datetime.now().strftime("%Y-%m-%d %H:%M:%S"), data['message_type'])
        return "OK"
        
    def getPluginInfo(self) -> dict:
        return {
            'name': 'mddstatus',
            'description': '麦当劳查询',
            'commandDescription': '-mdd',
            'usePlace': ['group', 'private', ],
            'showInHelp': True,
            'pluginConfigTableNames': [],
            'version': '1.0.3',
            'author': 'Teruteru',
        }
def getMddStatus()->Union[None, dict]:
    req = requests.get(mddUrl, headers=mddHeaders)
    if req.status_code != requests.codes.ok:
        warning('mdd api failed!')
        return None
    else:
        return req.json()