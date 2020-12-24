# -*- coding:utf-8 -*-

import os
import sys
import json
import time
import base64
import pymysql
import requests
from math import ceil
from io import BytesIO
import threadpool
import subprocess
import re

#保存结果的文件
# sku = []
# if os.path.exists("/root/Scripts/ai_color.txt"):
#     with open("/root/Scripts/ai_color.txt", "rb") as fr:
#         skus = [x.replace("\n","").split(":")[0] for x in fr.readlines()]

# #----------------------------------------舍弃
#table_name = "goods5_zengliang1"

# # 查询数据
#conn = pymysql.connect(host='115.28.187.85', port=3306, user='root', passwd='Ss.768754763', db='audit_db')
#cursor = conn.cursor()


#sql = "select sku from "+table_name+" limit 10"
#sql = "select sku from "+table_name+" "
#cursor.execute(sql)

# #查询到的所有sku列表
#result_tuple = cursor.fetchall()

#result = []

#for i in result_tuple:
 #   result.append(i[0])

#print(len(result))





#conn.commit()
#conn.close()
#--------------------------------------------------------------------




# json.dumps（）函数引起的。dumps是将dict数据转化为str数据，但是dict数据中包含byte数据所以会报错。
# 解决：编写一个解码类 遇到byte就转为str
# 将json.dumps（data）改写为json.dumps(data,cls=MyEncoder,indent=4)
class MyEncoder(json.JSONEncoder):

    def default(self, obj):
    
        if isinstance(obj, bytes):
            return str(obj, encoding='utf-8')
        
        return json.JSONEncoder.default(self, obj)


# ------------------------------------------------------------------

# init
oss_path = 'oss://lux-img-std-zjk/g/'

AI_result_path = '/home/AI_12/'

imgUrl = "https://lux-img-std-zjk.oss-cn-zhangjiakou-internal.aliyuncs.com/g/%s/1.jpg"

# imgUrl = "https://lux-std-img.oss-cn-hongkong-internal.aliyuncs.com/g/%s/1.jpg"
# imgUrl = "https://lux-std-img.oss-cn-hongkong.aliyuncs.com/g/%s/1.jpg"
# imgUrl = "https://lux-img-std-zjk.oss-cn-zhangjiakou-internal.aliyuncs.com/g/%s/1.jpg"
modelUrl = "https://aip.baidubce.com/rpc/2.0/ai_custom/v1/classification/bete1"

qps = 10
match = {}
top_num = 5
all_match = {}

dir_dict = {}
dir_lst = []


# 0.从oss中读取图片sku

# oss命令,返回文件夹名
oss_extract_cmd = "ossutil64 ls -d " + oss_path 

# 需要从os中获取到返回的内容
img_sku_lst = subprocess.getstatusoutput(oss_extract_cmd)[1].split('\n')[1:-3]

sku_lst = []

for i in img_sku_lst:
    sku_lst.append(re.findall('g/(.*?)/', i)[0])

# 排序后取前2000条

result = sorted(sku_lst)[35000:40000]


print(len(result))





# 1. 获取token
AK = "Wk3iBTcd6v4dEB6H6w5PtHDO"
SK = "6j5ZkdIx1T0NCphC8q5R9HOve4GDE7lL"

def get_token(AK, SK):
    host = 'https://aip.baidubce.com/oauth/2.0/token?grant_type=client_credentials&client_id='+AK+'&client_secret='+SK
    response = requests.get(host)
    return response.json()['access_token']

access_token = get_token(AK, SK)

headers = {"Content-Type": "application/json"}


# 2. 获取url图片 - - - - 舍弃读取图片部分 - - 保留图片加密为base64格式
def get_img_base64_value_from_url(url):
    try:
        r = requests.get(url)
        if r.status_code == 200:
            return base64.b64encode(BytesIO(r.content).read())
        else:
            return ""
    except Exception as e:
        print(e)
        return ""

fw = open(AI_result_path + "ai_color.txt","a")


# 定义线程池，指定线程数
pool = threadpool.ThreadPool(qps, poll_timeout=None)

# 识别函数 - 通过函数传sku
def ai(sku):
    global access_token

    n = ""
    msid = ""

    flag = False

    if modelUrl:
        image = get_img_base64_value_from_url(imgUrl % sku)
        if image:
            params = {"image": image, "top_num": str(top_num)}
            params = json.dumps(params, cls=MyEncoder,indent=4)
            request_url = modelUrl + "?access_token=" + access_token
            res = requests.post(request_url, data=params, headers=headers)
            if res.status_code == 200:
                response = res.json() or {}
                if response:
                    if "error_msg" in response.keys():
                        error_code = response["error_code"]
                        error_msg = response["error_msg"]
                        if error_code == 4:
                            pass
                        elif error_code in (13, 100, 110, 111):
                            access_token = get_token(AK, SK)           
                        fw.write(sku+":"+error_msg)
                        print(error_code, error_msg)
                    else:
                        log_id = response["log_id"]
                        results = response["results"]
                        matchs = sorted([(x["score"], x["name"]) for x in results if x["name"]!="[default]"], reverse = True)
                        if matchs:
                            # [(0.5357239246368408, '31'), (0.19340036809444427, '33'), (0.064056396484375, '6'), (0.03680400922894478, '29'), (0.019305428490042686, '13')]
                            #for m in range(len(matchs)):
                                #fScore = round(float(matchs[m][0]) * 100)
                                #if fScore > 15:
                            fScore = matchs[0][0]
                            fMatch = matchs[0][1]
                            all_match[sku] = [fScore, fMatch]
                            fw.write(sku+"-"+str(fScore)+":"+fMatch+":"+str(fScore)+"\n")
                            flag = True
                        else:
                            fw.write(sku+":no match")
                else:
                    fw.write(sku+":no match")
    time.sleep(1)

t1 = time.time()


# result = ['1stdibs10000682', 
# '1stdibs10000842', '1stdibs10001022', '1stdibs10002742', '1stdibs10002762', '1stdibs10002792', '1stdibs10002872', '1stdibs10002912', '1stdibs10003052', '1stdibs10003092'
# ]

# main 部分                          - - 拿到一条数据, 然后取第一个属性
reqs = threadpool.makeRequests(ai, [str(x).lower() for x in result])
for req in reqs:
    pool.putRequest(req)
pool.wait()

fw.close()

# print(len(match))
print(len(all_match))

t2 = time.time()

print("ai_color time diff: "+str(t2 - t1))


# 第三步 保存

def mkdir(path):
  
    path = path.strip()
    path = path.rstrip('\\')

    isExists = os.path.exists(path)

    if not isExists:
        os.makedirs(path)
        print (path+' Directory or file created successfully!')
        return True
    else:
        print (path+' Directory or file already exists!')
        return False


def download_image(url):
    try:
        r = requests.get(url)
        if r.status_code == 200:
            return r.content
        else:
            return ""
    except Exception as e:
        print(e)
        return ""


def ai_classify(collections):
    for dir, sku in collections.items():
        sku_id = sku.split('-')[0]
        score = sku.split('-')[1]
        content = download_image(imgUrl % sku_id)
        fp = open(AI_result_path + dir + '/' + sku_id + "_" +  score + '.jpg', 'wb')
        fp.write(content)
        fp.close()
        time.sleep(1)


if os.path.exists(AI_result_path + "ai_color.txt"):
    with open(AI_result_path + "ai_color.txt", "r") as fr:
        skus = [x.replace("\n","").split(":")[0] for x in fr.readlines()]
    with open(AI_result_path + "ai_color.txt", "r") as fr:
        catelogs = [x.replace("\n","").split(":")[1] for x in fr.readlines()]

for sku, dir in zip(skus, catelogs):

    mkdir(AI_result_path + dir + '/')

    dir_dict[dir] = sku

    dir_lst.append(dir_dict)

    dir_dict = {}


t1 = time.time()

pool = threadpool.ThreadPool(qps, poll_timeout=None)

reqs = threadpool.makeRequests(ai_classify, [x for x in dir_lst])
for req in reqs:
    pool.putRequest(req)
pool.wait()

# for lst in dir_lst:
#     ai_classify(lst)

t2 = time.time()

print("ai_color time diff: "+str(t2 - t1))





