// static/js/map.js
// 預設台北101
const DEFAULT_CENTER = { lat: 25.033968, lng: 121.564468 };

let map, markerLayer;
let currentCenter = { ...DEFAULT_CENTER };
let currentRadius = 3;
let currentBrand  = '';

window.currentCenter = currentCenter;
window.currentRadius = currentRadius;
window.currentBrand  = currentBrand;

const AREAS = {
  "臺北市": {
    "中正區": {
      "lat": 25.0324049,
      "lng": 121.5198839
    },
    "大同區": {
      "lat": 25.0634243,
      "lng": 121.5130417
    },
    "中山區": {
      "lat": 25.0696992,
      "lng": 121.5381597
    },
    "松山區": {
      "lat": 25.059991,
      "lng": 121.5575876
    },
    "大安區": {
      "lat": 25.0267701,
      "lng": 121.5434446
    },
    "萬華區": {
      "lat": 25.0285899,
      "lng": 121.4979858
    },
    "信義區": {
      "lat": 25.0306208,
      "lng": 121.5716697
    },
    "士林區": {
      "lat": 25.125467,
      "lng": 121.5508473
    },
    "北投區": {
      "lat": 25.1480682,
      "lng": 121.5177992
    },
    "內湖區": {
      "lat": 25.0837062,
      "lng": 121.5923828
    },
    "南港區": {
      "lat": 25.0360093,
      "lng": 121.6097573
    },
    "文山區": {
      "lat": 24.9885793,
      "lng": 121.5736082
    }
  },
  "基隆市": {
    "仁愛區": {
      "lat": 25.1194542,
      "lng": 121.7434205
    },
    "信義區": {
      "lat": 25.1257658,
      "lng": 121.772646
    },
    "中正區": {
      "lat": 25.1436575,
      "lng": 121.7783549
    },
    "中山區": {
      "lat": 25.1498637,
      "lng": 121.7308913
    },
    "安樂區": {
      "lat": 25.1413952,
      "lng": 121.7078325
    },
    "暖暖區": {
      "lat": 25.08097,
      "lng": 121.7447344
    },
    "七堵區": {
      "lat": 25.1096203,
      "lng": 121.683628
    }
  },
  "新北市": {
    "萬里區": {
      "lat": 25.1757246,
      "lng": 121.6439307
    },
    "金山區": {
      "lat": 25.2171459,
      "lng": 121.6052639
    },
    "板橋區": {
      "lat": 25.0118645,
      "lng": 121.4579675
    },
    "汐止區": {
      "lat": 25.0733132,
      "lng": 121.6546992
    },
    "深坑區": {
      "lat": 24.9976751,
      "lng": 121.6200624
    },
    "石碇區": {
      "lat": 24.9471411,
      "lng": 121.6472277
    },
    "瑞芳區": {
      "lat": 25.0981293,
      "lng": 121.8232018
    },
    "平溪區": {
      "lat": 25.0260707,
      "lng": 121.7578817
    },
    "雙溪區": {
      "lat": 24.9969839,
      "lng": 121.8329822
    },
    "貢寮區": {
      "lat": 25.0248564,
      "lng": 121.9182466
    },
    "新店區": {
      "lat": 24.9303901,
      "lng": 121.5316565
    },
    "坪林區": {
      "lat": 24.9109707,
      "lng": 121.724223
    },
    "烏來區": {
      "lat": 24.788243,
      "lng": 121.5414806
    },
    "永和區": {
      "lat": 25.008102,
      "lng": 121.516745
    },
    "中和區": {
      "lat": 24.9908804,
      "lng": 121.4936744
    },
    "土城區": {
      "lat": 24.964251,
      "lng": 121.445737
    },
    "三峽區": {
      "lat": 24.8820977,
      "lng": 121.4163094
    },
    "樹林區": {
      "lat": 24.9797061,
      "lng": 121.401034
    },
    "鶯歌區": {
      "lat": 24.9566258,
      "lng": 121.3466269
    },
    "三重區": {
      "lat": 25.0628165,
      "lng": 121.4870977
    },
    "新莊區": {
      "lat": 25.0358303,
      "lng": 121.4367535
    },
    "泰山區": {
      "lat": 25.0554977,
      "lng": 121.4162785
    },
    "林口區": {
      "lat": 25.1000868,
      "lng": 121.3527235
    },
    "蘆洲區": {
      "lat": 25.0892717,
      "lng": 121.4712461
    },
    "五股區": {
      "lat": 25.0961475,
      "lng": 121.4332139
    },
    "八里區": {
      "lat": 25.1381276,
      "lng": 121.4138359
    },
    "淡水區": {
      "lat": 25.1890764,
      "lng": 121.463904
    },
    "三芝區": {
      "lat": 25.2315989,
      "lng": 121.515558
    },
    "石門區": {
      "lat": 25.2651808,
      "lng": 121.5692761
    }
  },
  "連江縣": {
    "南竿鄉": {
      "lat": 26.154321,
      "lng": 119.931128
    },
    "北竿鄉": {
      "lat": 26.225637,
      "lng": 119.994251
    },
    "莒光鄉": {
      "lat": 25.97298,
      "lng": 119.938877
    },
    "東引鄉": {
      "lat": 26.366101,
      "lng": 120.4903
    }
  },
  "宜蘭縣": {
    "宜蘭市": {
      "lat": 24.7502118,
      "lng": 121.7569358
    },
    "頭城鎮": {
      "lat": 24.9007588,
      "lng": 121.845797
    },
    "礁溪鄉": {
      "lat": 24.8114419,
      "lng": 121.7346606
    },
    "壯圍鄉": {
      "lat": 24.7518304,
      "lng": 121.8017622
    },
    "員山鄉": {
      "lat": 24.7419924,
      "lng": 121.6612282
    },
    "羅東鎮": {
      "lat": 24.6788482,
      "lng": 121.7701782
    },
    "三星鄉": {
      "lat": 24.6677197,
      "lng": 121.6642714
    },
    "大同鄉": {
      "lat": 24.5515208,
      "lng": 121.5040369
    },
    "五結鄉": {
      "lat": 24.6888734,
      "lng": 121.8058342
    },
    "冬山鄉": {
      "lat": 24.6421499,
      "lng": 121.760255
    },
    "蘇澳鎮": {
      "lat": 24.5546706,
      "lng": 121.8346892
    },
    "南澳鄉": {
      "lat": 24.4486406,
      "lng": 121.6560593
    },
    "釣魚臺列嶼": {
      "lat": 25.746396,
      "lng": 123.475482
    }
  },
  "新竹市": {
    "北區": {
      "lat": 24.8226954,
      "lng": 120.9491233
    },
    "東區": {
      "lat": 24.7902817,
      "lng": 120.9927505
    },
    "香山區": {
      "lat": 24.7710434,
      "lng": 120.9236727
    }
  },
  "新竹縣": {
    "竹北市": {
      "lat": 24.8381621,
      "lng": 120.9948704
    },
    "湖口鄉": {
      "lat": 24.8856634,
      "lng": 121.0517242
    },
    "新豐鄉": {
      "lat": 24.907313,
      "lng": 120.9956033
    },
    "新埔鎮": {
      "lat": 24.8413396,
      "lng": 121.0939886
    },
    "關西鎮": {
      "lat": 24.7851468,
      "lng": 121.1866221
    },
    "芎林鄉": {
      "lat": 24.7657116,
      "lng": 121.1046394
    },
    "寶山鄉": {
      "lat": 24.7369735,
      "lng": 120.9991605
    },
    "竹東鎮": {
      "lat": 24.730758,
      "lng": 121.0753632
    },
    "五峰鄉": {
      "lat": 24.578054,
      "lng": 121.1389495
    },
    "橫山鄉": {
      "lat": 24.7078092,
      "lng": 121.1469732
    },
    "尖石鄉": {
      "lat": 24.5949324,
      "lng": 121.2819341
    },
    "北埔鄉": {
      "lat": 24.672074,
      "lng": 121.0642745
    },
    "峨眉鄉": {
      "lat": 24.678112,
      "lng": 121.0110809
    }
  },
  "桃園市": {
    "中壢區": {
      "lat": 24.979938,
      "lng": 121.2147243
    },
    "平鎮區": {
      "lat": 24.9211792,
      "lng": 121.2140051
    },
    "龍潭區": {
      "lat": 24.8506495,
      "lng": 121.2117877
    },
    "楊梅區": {
      "lat": 24.9182099,
      "lng": 121.1291697
    },
    "新屋區": {
      "lat": 24.9728035,
      "lng": 121.067758
    },
    "觀音區": {
      "lat": 25.0267161,
      "lng": 121.1155021
    },
    "桃園區": {
      "lat": 25.0004002,
      "lng": 121.2996612
    },
    "龜山區": {
      "lat": 25.0241747,
      "lng": 121.3569265
    },
    "八德區": {
      "lat": 24.949689,
      "lng": 121.2913102
    },
    "大溪區": {
      "lat": 24.8679703,
      "lng": 121.296342
    },
    "復興區": {
      "lat": 24.7294988,
      "lng": 121.3754588
    },
    "大園區": {
      "lat": 25.0638471,
      "lng": 121.21177
    },
    "蘆竹區": {
      "lat": 25.0607334,
      "lng": 121.2831266
    }
  },
  "苗栗縣": {
    "竹南鎮": {
      "lat": 24.6986246,
      "lng": 120.8777316
    },
    "頭份市": {
      "lat": 24.6762824,
      "lng": 120.9189437
    },
    "三灣鄉": {
      "lat": 24.6359941,
      "lng": 120.9525745
    },
    "南庄鄉": {
      "lat": 24.5660843,
      "lng": 121.017471
    },
    "獅潭鄉": {
      "lat": 24.5197861,
      "lng": 120.9206688
    },
    "後龍鎮": {
      "lat": 24.6156265,
      "lng": 120.781205
    },
    "通霄鎮": {
      "lat": 24.4850464,
      "lng": 120.7146378
    },
    "苑裡鎮": {
      "lat": 24.4110232,
      "lng": 120.6882195
    },
    "苗栗市": {
      "lat": 24.5638214,
      "lng": 120.8112299
    },
    "造橋鄉": {
      "lat": 24.6248131,
      "lng": 120.8695663
    },
    "頭屋鄉": {
      "lat": 24.573455,
      "lng": 120.8826631
    },
    "公館鄉": {
      "lat": 24.5024969,
      "lng": 120.8505904
    },
    "大湖鄉": {
      "lat": 24.3935964,
      "lng": 120.8631192
    },
    "泰安鄉": {
      "lat": 24.4192582,
      "lng": 121.0681571
    },
    "銅鑼鄉": {
      "lat": 24.4559183,
      "lng": 120.7992043
    },
    "三義鄉": {
      "lat": 24.3808166,
      "lng": 120.7701929
    },
    "西湖鄉": {
      "lat": 24.5415322,
      "lng": 120.7614144
    },
    "卓蘭鎮": {
      "lat": 24.3251017,
      "lng": 120.8561966
    }
  },
  "臺中市": {
    "中區": {
      "lat": 24.1416857,
      "lng": 120.680598
    },
    "東區": {
      "lat": 24.1373321,
      "lng": 120.6970865
    },
    "南區": {
      "lat": 24.1211411,
      "lng": 120.6646178
    },
    "西區": {
      "lat": 24.1439108,
      "lng": 120.6647579
    },
    "北區": {
      "lat": 24.1586399,
      "lng": 120.6809521
    },
    "北屯區": {
      "lat": 24.184003,
      "lng": 120.7362319
    },
    "西屯區": {
      "lat": 24.1830889,
      "lng": 120.6270131
    },
    "南屯區": {
      "lat": 24.1416552,
      "lng": 120.6177379
    },
    "太平區": {
      "lat": 24.1147738,
      "lng": 120.7734217
    },
    "大里區": {
      "lat": 24.0957574,
      "lng": 120.6926261
    },
    "霧峰區": {
      "lat": 24.0433279,
      "lng": 120.7201989
    },
    "烏日區": {
      "lat": 24.0839271,
      "lng": 120.6293305
    },
    "豐原區": {
      "lat": 24.249903,
      "lng": 120.7375715
    },
    "后里區": {
      "lat": 24.3096248,
      "lng": 120.7146127
    },
    "石岡區": {
      "lat": 24.264933,
      "lng": 120.7903822
    },
    "東勢區": {
      "lat": 24.2495264,
      "lng": 120.8401401
    },
    "和平區": {
      "lat": 24.2762028,
      "lng": 121.140185
    },
    "新社區": {
      "lat": 24.1776929,
      "lng": 120.8313228
    },
    "潭子區": {
      "lat": 24.2117112,
      "lng": 120.710997
    },
    "大雅區": {
      "lat": 24.2270418,
      "lng": 120.6411818
    },
    "神岡區": {
      "lat": 24.2656801,
      "lng": 120.6733321
    },
    "大肚區": {
      "lat": 24.144675,
      "lng": 120.5543243
    },
    "沙鹿區": {
      "lat": 24.2342521,
      "lng": 120.5838628
    },
    "龍井區": {
      "lat": 24.2006289,
      "lng": 120.5283728
    },
    "梧棲區": {
      "lat": 24.2455243,
      "lng": 120.5301259
    },
    "清水區": {
      "lat": 24.2920574,
      "lng": 120.5809094
    },
    "大甲區": {
      "lat": 24.3782716,
      "lng": 120.6357901
    },
    "外埔區": {
      "lat": 24.3355107,
      "lng": 120.6650639
    },
    "大安區": {
      "lat": 24.3650955,
      "lng": 120.5914407
    }
  },
  "彰化縣": {
    "彰化市": {
      "lat": 24.0753291,
      "lng": 120.5694208
    },
    "芬園鄉": {
      "lat": 24.0062879,
      "lng": 120.6294414
    },
    "花壇鄉": {
      "lat": 24.0300688,
      "lng": 120.5597655
    },
    "秀水鄉": {
      "lat": 24.0324941,
      "lng": 120.5041184
    },
    "鹿港鎮": {
      "lat": 24.0828668,
      "lng": 120.4385491
    },
    "福興鄉": {
      "lat": 24.0302167,
      "lng": 120.4310511
    },
    "線西鄉": {
      "lat": 24.1315813,
      "lng": 120.452157
    },
    "和美鎮": {
      "lat": 24.1137954,
      "lng": 120.5112045
    },
    "伸港鄉": {
      "lat": 24.1636711,
      "lng": 120.486449
    },
    "員林市": {
      "lat": 23.9565045,
      "lng": 120.593073
    },
    "社頭鄉": {
      "lat": 23.9053641,
      "lng": 120.6021661
    },
    "永靖鄉": {
      "lat": 23.9213951,
      "lng": 120.5416032
    },
    "埔心鄉": {
      "lat": 23.9527752,
      "lng": 120.5342802
    },
    "溪湖鎮": {
      "lat": 23.9517146,
      "lng": 120.4831739
    },
    "大村鄉": {
      "lat": 23.9920921,
      "lng": 120.5586866
    },
    "埔鹽鄉": {
      "lat": 23.9920442,
      "lng": 120.4594626
    },
    "田中鎮": {
      "lat": 23.8572387,
      "lng": 120.5903471
    },
    "北斗鎮": {
      "lat": 23.867574,
      "lng": 120.5331566
    },
    "田尾鄉": {
      "lat": 23.9005606,
      "lng": 120.5223244
    },
    "埤頭鄉": {
      "lat": 23.8823412,
      "lng": 120.4675642
    },
    "溪州鄉": {
      "lat": 23.8272518,
      "lng": 120.5224904
    },
    "竹塘鄉": {
      "lat": 23.8505872,
      "lng": 120.4136645
    },
    "二林鎮": {
      "lat": 23.9162141,
      "lng": 120.404225
    },
    "大城鄉": {
      "lat": 23.8506928,
      "lng": 120.3113284
    },
    "芳苑鄉": {
      "lat": 23.9537906,
      "lng": 120.3539226
    },
    "二水鄉": {
      "lat": 23.8092402,
      "lng": 120.628589
    }
  },
  "南投縣": {
    "南投市": {
      "lat": 23.9217354,
      "lng": 120.6787658
    },
    "中寮鄉": {
      "lat": 23.9058921,
      "lng": 120.7859159
    },
    "草屯鎮": {
      "lat": 23.9832108,
      "lng": 120.7326182
    },
    "國姓鄉": {
      "lat": 24.0313541,
      "lng": 120.8676052
    },
    "埔里鎮": {
      "lat": 23.9789259,
      "lng": 120.9625259
    },
    "仁愛鄉": {
      "lat": 24.0288651,
      "lng": 121.1443879
    },
    "名間鄉": {
      "lat": 23.8510771,
      "lng": 120.6774402
    },
    "集集鎮": {
      "lat": 23.8370169,
      "lng": 120.7854192
    },
    "水里鄉": {
      "lat": 23.7961291,
      "lng": 120.8622721
    },
    "魚池鄉": {
      "lat": 23.8760121,
      "lng": 120.9256736
    },
    "信義鄉": {
      "lat": 23.6554647,
      "lng": 121.0212867
    },
    "竹山鎮": {
      "lat": 23.6980552,
      "lng": 120.7100797
    },
    "鹿谷鄉": {
      "lat": 23.7377603,
      "lng": 120.7815065
    }
  },
  "嘉義市": {
    "西區": {
      "lat": 23.4791553,
      "lng": 120.4248724
    },
    "東區": {
      "lat": 23.4817033,
      "lng": 120.4706244
    }
  },
  "嘉義縣": {
    "番路鄉": {
      "lat": 23.4276567,
      "lng": 120.6075335
    },
    "梅山鄉": {
      "lat": 23.5553547,
      "lng": 120.6387459
    },
    "竹崎鄉": {
      "lat": 23.5037653,
      "lng": 120.5965771
    },
    "阿里山鄉": {
      "lat": 23.4407762,
      "lng": 120.7596173
    },
    "中埔鄉": {
      "lat": 23.40409,
      "lng": 120.5365312
    },
    "大埔鄉": {
      "lat": 23.2884843,
      "lng": 120.5896466
    },
    "水上鄉": {
      "lat": 23.4291129,
      "lng": 120.4147357
    },
    "鹿草鄉": {
      "lat": 23.4081174,
      "lng": 120.3045468
    },
    "太保市": {
      "lat": 23.4729191,
      "lng": 120.3440009
    },
    "朴子市": {
      "lat": 23.4461061,
      "lng": 120.2538977
    },
    "東石鄉": {
      "lat": 23.4686606,
      "lng": 120.1738682
    },
    "六腳鄉": {
      "lat": 23.5102098,
      "lng": 120.2714728
    },
    "新港鄉": {
      "lat": 23.5458129,
      "lng": 120.3482873
    },
    "民雄鄉": {
      "lat": 23.5425535,
      "lng": 120.4442798
    },
    "大林鎮": {
      "lat": 23.5989083,
      "lng": 120.4807865
    },
    "溪口鄉": {
      "lat": 23.5935309,
      "lng": 120.4010282
    },
    "義竹鄉": {
      "lat": 23.3457587,
      "lng": 120.2239433
    },
    "布袋鎮": {
      "lat": 23.3749428,
      "lng": 120.1777498
    }
  },
  "雲林縣": {
    "斗南鎮": {
      "lat": 23.6706639,
      "lng": 120.4826356
    },
    "大埤鄉": {
      "lat": 23.6455971,
      "lng": 120.4255592
    },
    "虎尾鎮": {
      "lat": 23.7166154,
      "lng": 120.4293061
    },
    "土庫鎮": {
      "lat": 23.6911066,
      "lng": 120.3647252
    },
    "褒忠鄉": {
      "lat": 23.716132,
      "lng": 120.3116122
    },
    "東勢鄉": {
      "lat": 23.6961232,
      "lng": 120.2564173
    },
    "臺西鄉": {
      "lat": 23.7160082,
      "lng": 120.2054952
    },
    "崙背鄉": {
      "lat": 23.7784979,
      "lng": 120.3339769
    },
    "麥寮鄉": {
      "lat": 23.7881706,
      "lng": 120.243533
    },
    "斗六市": {
      "lat": 23.7065188,
      "lng": 120.5600044
    },
    "林內鄉": {
      "lat": 23.7557209,
      "lng": 120.6155018
    },
    "古坑鄉": {
      "lat": 23.6254547,
      "lng": 120.6117351
    },
    "莿桐鄉": {
      "lat": 23.7697389,
      "lng": 120.5290419
    },
    "西螺鎮": {
      "lat": 23.7794211,
      "lng": 120.4580795
    },
    "二崙鄉": {
      "lat": 23.7925521,
      "lng": 120.3964598
    },
    "北港鎮": {
      "lat": 23.5921953,
      "lng": 120.2940164
    },
    "水林鄉": {
      "lat": 23.5616285,
      "lng": 120.2352734
    },
    "口湖鄉": {
      "lat": 23.553654,
      "lng": 120.1413711
    },
    "四湖鄉": {
      "lat": 23.6420687,
      "lng": 120.2064699
    },
    "元長鄉": {
      "lat": 23.642431,
      "lng": 120.3279617
    }
  },
  "臺南市": {
    "中西區": {
      "lat": 22.9959446,
      "lng": 120.192874
    },
    "東區": {
      "lat": 22.981782,
      "lng": 120.2281858
    },
    "南區": {
      "lat": 22.9556186,
      "lng": 120.1903743
    },
    "北區": {
      "lat": 23.0101218,
      "lng": 120.2068735
    },
    "安平區": {
      "lat": 22.9900844,
      "lng": 120.1649949
    },
    "安南區": {
      "lat": 23.0486968,
      "lng": 120.1526189
    },
    "永康區": {
      "lat": 23.0272953,
      "lng": 120.2542795
    },
    "歸仁區": {
      "lat": 22.9467947,
      "lng": 120.2930627
    },
    "新化區": {
      "lat": 23.0339455,
      "lng": 120.3357964
    },
    "左鎮區": {
      "lat": 23.0260461,
      "lng": 120.4123917
    },
    "玉井區": {
      "lat": 23.1148093,
      "lng": 120.4609622
    },
    "楠西區": {
      "lat": 23.1788585,
      "lng": 120.5170304
    },
    "南化區": {
      "lat": 23.1151111,
      "lng": 120.5441223
    },
    "仁德區": {
      "lat": 22.9413093,
      "lng": 120.2418788
    },
    "關廟區": {
      "lat": 22.9557791,
      "lng": 120.3342821
    },
    "龍崎區": {
      "lat": 22.9548228,
      "lng": 120.3869373
    },
    "官田區": {
      "lat": 23.1909855,
      "lng": 120.3479918
    },
    "麻豆區": {
      "lat": 23.1824803,
      "lng": 120.241308
    },
    "佳里區": {
      "lat": 23.1669941,
      "lng": 120.178593
    },
    "西港區": {
      "lat": 23.1249189,
      "lng": 120.2002309
    },
    "七股區": {
      "lat": 23.1232658,
      "lng": 120.1005854
    },
    "將軍區": {
      "lat": 23.2083441,
      "lng": 120.1276958
    },
    "學甲區": {
      "lat": 23.2521981,
      "lng": 120.1841865
    },
    "北門區": {
      "lat": 23.2777708,
      "lng": 120.1262357
    },
    "新營區": {
      "lat": 23.3015249,
      "lng": 120.2954067
    },
    "後壁區": {
      "lat": 23.3620148,
      "lng": 120.3485081
    },
    "白河區": {
      "lat": 23.3513207,
      "lng": 120.4578565
    },
    "東山區": {
      "lat": 23.2783187,
      "lng": 120.4441211
    },
    "六甲區": {
      "lat": 23.2272672,
      "lng": 120.3800259
    },
    "下營區": {
      "lat": 23.2310398,
      "lng": 120.26484
    },
    "柳營區": {
      "lat": 23.26887,
      "lng": 120.3549205
    },
    "鹽水區": {
      "lat": 23.2979862,
      "lng": 120.2482977
    },
    "善化區": {
      "lat": 23.1403107,
      "lng": 120.2988274
    },
    "大內區": {
      "lat": 23.1448215,
      "lng": 120.3988147
    },
    "山上區": {
      "lat": 23.0968933,
      "lng": 120.370977
    },
    "新市區": {
      "lat": 23.083195,
      "lng": 120.2923941
    },
    "安定區": {
      "lat": 23.0997493,
      "lng": 120.2296235
    }
  },
  "高雄市": {
    "新興區": {
      "lat": 22.6299291,
      "lng": 120.3067337
    },
    "前金區": {
      "lat": 22.6269905,
      "lng": 120.2944217
    },
    "苓雅區": {
      "lat": 22.6235945,
      "lng": 120.3209103
    },
    "鹽埕區": {
      "lat": 22.6242459,
      "lng": 120.2842331
    },
    "鼓山區": {
      "lat": 22.6501952,
      "lng": 120.274163
    },
    "旗津區": {
      "lat": 22.5856558,
      "lng": 120.2891539
    },
    "前鎮區": {
      "lat": 22.5926972,
      "lng": 120.3146749
    },
    "三民區": {
      "lat": 22.6498988,
      "lng": 120.3179187
    },
    "楠梓區": {
      "lat": 22.7210996,
      "lng": 120.300758
    },
    "小港區": {
      "lat": 22.5514021,
      "lng": 120.3592605
    },
    "左營區": {
      "lat": 22.683957,
      "lng": 120.2951588
    },
    "仁武區": {
      "lat": 22.7012078,
      "lng": 120.3605265
    },
    "大社區": {
      "lat": 22.7398348,
      "lng": 120.3707994
    },
    "岡山區": {
      "lat": 22.8050589,
      "lng": 120.2978906
    },
    "路竹區": {
      "lat": 22.8572417,
      "lng": 120.2659871
    },
    "阿蓮區": {
      "lat": 22.8702288,
      "lng": 120.3210967
    },
    "田寮區": {
      "lat": 22.8639431,
      "lng": 120.3959842
    },
    "燕巢區": {
      "lat": 22.7876963,
      "lng": 120.370799
    },
    "橋頭區": {
      "lat": 22.752524,
      "lng": 120.3006534
    },
    "梓官區": {
      "lat": 22.748209,
      "lng": 120.2593989
    },
    "彌陀區": {
      "lat": 22.7794453,
      "lng": 120.2394571
    },
    "永安區": {
      "lat": 22.8222459,
      "lng": 120.228051
    },
    "湖內區": {
      "lat": 22.8932495,
      "lng": 120.2259375
    },
    "鳳山區": {
      "lat": 22.6137925,
      "lng": 120.3554359
    },
    "大寮區": {
      "lat": 22.5928358,
      "lng": 120.4111468
    },
    "林園區": {
      "lat": 22.5081374,
      "lng": 120.399052
    },
    "鳥松區": {
      "lat": 22.662493,
      "lng": 120.3727783
    },
    "大樹區": {
      "lat": 22.7110036,
      "lng": 120.425407
    },
    "旗山區": {
      "lat": 22.8649703,
      "lng": 120.4754554
    },
    "美濃區": {
      "lat": 22.9000553,
      "lng": 120.5634635
    },
    "六龜區": {
      "lat": 23.0119543,
      "lng": 120.6585635
    },
    "內門區": {
      "lat": 22.9566882,
      "lng": 120.4719272
    },
    "杉林區": {
      "lat": 22.9969468,
      "lng": 120.5621971
    },
    "甲仙區": {
      "lat": 23.1165499,
      "lng": 120.6232895
    },
    "桃源區": {
      "lat": 23.2249459,
      "lng": 120.8523383
    },
    "那瑪夏區": {
      "lat": 23.275008,
      "lng": 120.741944
    },
    "茂林區": {
      "lat": 22.9199326,
      "lng": 120.752384
    },
    "茄萣區": {
      "lat": 22.882414,
      "lng": 120.1980519
    }
  },
  "南海諸": {
    "島東沙群島": {
      "lat": 20.705842,
      "lng": 116.906984
    },
    "島南沙群島": {
      "lat": 10.724232,
      "lng": 115.812406
    }
  },
  "澎湖縣": {
    "馬公市": {
      "lat": 23.55534,
      "lng": 119.59234
    },
    "西嶼鄉": {
      "lat": 23.59975,
      "lng": 119.50783
    },
    "望安鄉": {
      "lat": 23.36904,
      "lng": 119.50406
    },
    "七美鄉": {
      "lat": 23.20108,
      "lng": 119.43393
    },
    "白沙鄉": {
      "lat": 23.64178,
      "lng": 119.59251
    },
    "湖西鄉": {
      "lat": 23.57364,
      "lng": 119.64462
    }
  },
  "金門縣": {
    "金沙鎮": {
      "lat": 24.45865,
      "lng": 118.40841
    },
    "金湖鎮": {
      "lat": 24.41496,
      "lng": 118.40373
    },
    "金寧鄉": {
      "lat": 24.42482,
      "lng": 118.31705
    },
    "金城鎮": {
      "lat": 24.38402,
      "lng": 118.30128
    },
    "烈嶼鄉": {
      "lat": 24.40166,
      "lng": 118.22789
    },
    "烏坵鄉": {
      "lat": 24.992338,
      "lng": 119.452738
    }
  },
  "屏東縣": {
    "屏東市": {
      "lat": 22.6647375,
      "lng": 120.4799948
    },
    "三地門鄉": {
      "lat": 22.7978685,
      "lng": 120.6865219
    },
    "霧臺鄉": {
      "lat": 22.7599048,
      "lng": 120.8008099
    },
    "瑪家鄉": {
      "lat": 22.6710776,
      "lng": 120.6799239
    },
    "九如鄉": {
      "lat": 22.7316677,
      "lng": 120.4845044
    },
    "里港鄉": {
      "lat": 22.7985483,
      "lng": 120.5061276
    },
    "高樹鄉": {
      "lat": 22.8099202,
      "lng": 120.6017678
    },
    "鹽埔鄉": {
      "lat": 22.7425364,
      "lng": 120.5693941
    },
    "長治鄉": {
      "lat": 22.6945495,
      "lng": 120.555979
    },
    "麟洛鄉": {
      "lat": 22.6487637,
      "lng": 120.5299693
    },
    "竹田鄉": {
      "lat": 22.5885564,
      "lng": 120.5266379
    },
    "內埔鄉": {
      "lat": 22.6511693,
      "lng": 120.5888222
    },
    "萬丹鄉": {
      "lat": 22.5884955,
      "lng": 120.4766188
    },
    "潮州鎮": {
      "lat": 22.5364295,
      "lng": 120.5568063
    },
    "泰武鄉": {
      "lat": 22.6040848,
      "lng": 120.6917929
    },
    "來義鄉": {
      "lat": 22.5015721,
      "lng": 120.6857232
    },
    "萬巒鄉": {
      "lat": 22.5823346,
      "lng": 120.601817
    },
    "崁頂鄉": {
      "lat": 22.5152815,
      "lng": 120.5006598
    },
    "新埤鄉": {
      "lat": 22.4867628,
      "lng": 120.5846257
    },
    "南州鄉": {
      "lat": 22.479807,
      "lng": 120.5180561
    },
    "林邊鄉": {
      "lat": 22.441421,
      "lng": 120.5125095
    },
    "東港鎮": {
      "lat": 22.4626563,
      "lng": 120.4751333
    },
    "琉球鄉": {
      "lat": 22.3400028,
      "lng": 120.3710466
    },
    "佳冬鄉": {
      "lat": 22.4298062,
      "lng": 120.5476124
    },
    "新園鄉": {
      "lat": 22.5171903,
      "lng": 120.4501429
    },
    "枋寮鄉": {
      "lat": 22.403342,
      "lng": 120.5975845
    },
    "枋山鄉": {
      "lat": 22.2708696,
      "lng": 120.6567673
    },
    "春日鄉": {
      "lat": 22.4039975,
      "lng": 120.6975799
    },
    "獅子鄉": {
      "lat": 22.2608492,
      "lng": 120.7356454
    },
    "車城鄉": {
      "lat": 22.0791562,
      "lng": 120.7432633
    },
    "牡丹鄉": {
      "lat": 22.1555286,
      "lng": 120.8173609
    },
    "恆春鎮": {
      "lat": 21.9853164,
      "lng": 120.7632537
    },
    "滿州鄉": {
      "lat": 22.0493002,
      "lng": 120.8435675
    }
  },
  "臺東縣": {
    "臺東市": {
      "lat": 22.7516572,
      "lng": 121.1103647
    },
    "綠島鄉": {
      "lat": 22.6601754,
      "lng": 121.4901951
    },
    "蘭嶼鄉": {
      "lat": 22.0461683,
      "lng": 121.5508328
    },
    "延平鄉": {
      "lat": 22.9034317,
      "lng": 120.9831902
    },
    "卑南鄉": {
      "lat": 22.7649445,
      "lng": 121.0015521
    },
    "鹿野鄉": {
      "lat": 22.9512567,
      "lng": 121.1560376
    },
    "關山鎮": {
      "lat": 23.0378068,
      "lng": 121.1766197
    },
    "海端鄉": {
      "lat": 23.1147853,
      "lng": 121.0175672
    },
    "池上鄉": {
      "lat": 23.0924871,
      "lng": 121.2184501
    },
    "東河鄉": {
      "lat": 22.9800692,
      "lng": 121.2517917
    },
    "成功鎮": {
      "lat": 23.1266372,
      "lng": 121.3537983
    },
    "長濱鄉": {
      "lat": 23.334769,
      "lng": 121.4261725
    },
    "太麻里鄉": {
      "lat": 22.5909808,
      "lng": 120.9797643
    },
    "金峰鄉": {
      "lat": 22.5816169,
      "lng": 120.8570384
    },
    "大武鄉": {
      "lat": 22.3835952,
      "lng": 120.8991703
    },
    "達仁鄉": {
      "lat": 22.3843072,
      "lng": 120.8355239
    }
  },
  "花蓮縣": {
    "花蓮市": {
      "lat": 23.9970027,
      "lng": 121.6071463
    },
    "新城鄉": {
      "lat": 24.0557995,
      "lng": 121.6137969
    },
    "秀林鄉": {
      "lat": 24.1237441,
      "lng": 121.4807194
    },
    "吉安鄉": {
      "lat": 23.9554658,
      "lng": 121.5646738
    },
    "壽豐鄉": {
      "lat": 23.8445971,
      "lng": 121.5341569
    },
    "鳳林鎮": {
      "lat": 23.7432446,
      "lng": 121.4698848
    },
    "光復鄉": {
      "lat": 23.6465874,
      "lng": 121.4351231
    },
    "豐濱鄉": {
      "lat": 23.5851943,
      "lng": 121.4942331
    },
    "瑞穗鄉": {
      "lat": 23.5156124,
      "lng": 121.4073472
    },
    "萬榮鄉": {
      "lat": 23.7277263,
      "lng": 121.3189531
    },
    "玉里鎮": {
      "lat": 23.3714359,
      "lng": 121.3604476
    },
    "卓溪鄉": {
      "lat": 23.3906288,
      "lng": 121.1804222
    },
    "富里鄉": {
      "lat": 23.1967209,
      "lng": 121.2980494
    }
  }
};

// ---- 工具 ----
function readCenterFromDataset() {
  const el = document.getElementById('map');
  if (!el) return;
  const lat = parseFloat(el.dataset.centerLat || `${DEFAULT_CENTER.lat}`);
  const lng = parseFloat(el.dataset.centerLng || `${DEFAULT_CENTER.lng}`);
  const r   = parseFloat(el.dataset.radiusKm  || '3');
  currentCenter = { lat, lng };
  currentRadius = r;
  window.currentCenter = currentCenter;
  window.currentRadius = currentRadius;
}

async function postCenter(lat, lng, radius) {
  const form = new FormData();
  form.append('lat', String(lat));
  form.append('lng', String(lng));
  if (Number.isFinite(radius)) form.append('radius_km', String(radius));
  await fetch('/set_center', { method: 'POST', body: form, credentials: 'same-origin' });
  location.reload(); // 重新整理，讓上方卡片的距離也一起更新
}

// ---- 地圖與店家 ----
function initMap(center = DEFAULT_CENTER, radiusKm = 3, brand = '') {
  currentCenter = center;
  currentRadius = radiusKm;
  currentBrand  = brand || currentBrand;
  window.currentCenter = currentCenter;
  window.currentRadius = currentRadius;
  window.currentBrand  = currentBrand;

  if (!map) {
    map = L.map("map").setView([center.lat, center.lng], 13);
    L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
      maxZoom: 19,
      attribution: '&copy; OpenStreetMap contributors'
    }).addTo(map);
    markerLayer = L.layerGroup().addTo(map);
  } else {
    map.setView([center.lat, center.lng], 13);
    markerLayer.clearLayers();
  }

  drawMarkers(center, radiusKm, currentBrand);
}

function drawMarkers(center, radiusKm, brand) {
  const brandQuery = brand ? `&brand=${encodeURIComponent(brand)}` : "";
  fetch(`/api/stores?lat=${center.lat}&lng=${center.lng}&radius=${radiusKm}${brandQuery}`)
    .then(r => r.json())
    .then(stores => {
    
    var userIcon = L.divIcon({
    className: 'custom-div-icon',
    html: "<div class='avatar-marker rounded-circle bg-primary-subtle d-flex justify-content-center align-items-center'>👤</div>",
    iconSize: [35, 35],
    iconAnchor: [17, 35],
    popupAnchor: [0, -35]
});
    L.marker(center, {
    icon: userIcon
    }).addTo(markerLayer)
    .bindPopup("你的位置")
    .openPopup();
      stores.forEach(s => {
        const Brand_Color = {
        "7-11" : '#00FF22',
        'familymart':'#0080FF',
        'hilife':'#FF0000',
        'okmart':'#FF9D00',
        'Other':'#FF00F2'
      }
        const circlecolor = Brand_Color[s.brand]
        const hasStock = (s.remaining_qty || 0) > 0;
        const circle = L.circleMarker([s.latitude, s.longitude], {
          // 藍色=有即時品；灰色=無
          color: hasStock ? circlecolor : "#6c757d",
          fillColor: hasStock ? circlecolor : "#c7c8ca",
          fillOpacity: 0.7,
          weight: 2,
          radius: Math.max(8, Math.min(80, (s.remaining_qty || 0))) / 5
        }).addTo(markerLayer);
        circle.bindPopup(`
          <div><strong>${s.name}</strong> ${s.brand ? `<span class="badge bg-secondary ms-1">${s.brand}</span>` : ""}</div>
          <div class="text-muted">${s.address || ""}</div>
          <div>剩餘量：${s.remaining_qty || 0}</div>
          ${s.distance_km !== undefined ? `<div class="text-muted small">距離：約 ${s.distance_km} 公里</div>` : ""}
          <a class="btn btn-primary btn-sm mt-2" href="/store/${s.id}">查看店家</a>
        `);
      });
    });
}

// ---- UI：地址選擇與定位 ----
function fillAddressSelectors(){
  const cSel = document.getElementById("countySel");
  const tSel = document.getElementById("townSel");
  if (!cSel || !tSel) return;

  cSel.innerHTML = Object.keys(AREAS).map(c => `<option value="${c}">${c}</option>`).join("");
  function refreshTown(){
    const c = cSel.value;
    const towns = AREAS[c] || {};
    tSel.innerHTML = Object.keys(towns).map(t => `<option value="${t}">${t}</option>`).join("");
  }
  cSel.addEventListener("change", refreshTown);
  cSel.value = "台北市"; refreshTown(); tSel.value = "信義區";
}

function askGeo() {
  if (!navigator.geolocation) { showSelector(); return; }
  navigator.geolocation.getCurrentPosition(
    async (pos) => {
      await postCenter(pos.coords.latitude, pos.coords.longitude, currentRadius);
    },
    () => showSelector(),
    { enableHighAccuracy: true, timeout: 8000, maximumAge: 0 }
  );
}

function showSelector(){
  const modalEl = document.getElementById("locModal");
  const bsModal = modalEl ? new bootstrap.Modal(modalEl) : null;
  fillAddressSelectors();
  bsModal?.show();

  const btn = document.getElementById("applySelect");
  if (!btn) return;
  btn.onclick = async () => {
    const county = document.getElementById("countySel")?.value || "";
    const town   = document.getElementById("townSel")?.value || "";
    const r      = parseFloat(document.getElementById("radiusInput")?.value || currentRadius);

    const area = AREAS[county] || {};
    const base = (area[town]) || area || DEFAULT_CENTER; // 安全取得
    await postCenter(base.lat, base.lng, r);
  };
}
// 全域變數和常數
const ADDRESS_HISTORY_KEY = 'address_history';
const MAX_HISTORY_SIZE = 5;

// 從 localStorage 載入歷史紀錄
function loadAddressHistory() {
    try {
        const history = localStorage.getItem(ADDRESS_HISTORY_KEY);
        return history ? JSON.parse(history) : [];
    } catch (e) {
        console.error("無法載入地址歷史紀錄", e);
        return [];
    }
}

// 將新的地址新增到歷史紀錄
function addAddressToHistory(address) {
    if (!address) return;
    const history = loadAddressHistory();
    const uniqueHistory = history.filter(item => item !== address);
    uniqueHistory.unshift(address);
    const limitedHistory = uniqueHistory.slice(0, MAX_HISTORY_SIZE);
    try {
        localStorage.setItem(ADDRESS_HISTORY_KEY, JSON.stringify(limitedHistory));
    } catch (e) {
        console.error("無法儲存地址歷史紀錄", e);
    }
    renderAddressHistory(limitedHistory);
}

//渲染歷史紀錄到 datalist
function renderAddressHistory(history) {
    const datalist = document.getElementById('addressHistoryList');
    if (!datalist) return;
    datalist.innerHTML = '';
    history.forEach(address => {
        const option = document.createElement('option');
        option.value = address;
        datalist.appendChild(option);
    });
}
function getCoordinates() {
        const address = document.getElementById('addressInput').value;
        const resultDiv = document.getElementById('result');

        if (!address) {
            resultDiv.innerHTML = '<span class="text-danger">請輸入一個地址。</span>';
            return;
        }

        resultDiv.innerHTML = '<span>載入中...</span>';

        const url = new URL('https://nominatim.openstreetmap.org/search');
        url.searchParams.append('q', address);
        url.searchParams.append('format', 'json');
        url.searchParams.append('limit', 1);
        url.searchParams.append('countrycodes', 'tw');

        fetch(url, {
            headers: {
                'User-Agent': 'FoodMapApp/1.0 (948794konya@gmail.com)'
            }
        })
        .then(response => {
            if (!response.ok) {
                throw new Error(`API 請求失敗，狀態碼：${response.status}`);
            }
            return response.json();
        })
        .then(data => {
            if (data && data.length > 0) {
                const lat = data[0].lat;
                const lng = data[0].lon;
                currentCenter = { lat: lat, lng: lng };
                initMap(currentCenter, currentRadius, currentBrand)
                resultDiv.innerHTML = '<span>定位成功</span>';
                addAddressToHistory(address);
            } else {
                resultDiv.innerHTML = '<div class="alert alert-warning mt-2 py-2">找不到該地址的經緯度。</div>';
            }
        })
        .catch(error => {
            resultDiv.innerHTML = `<div class="alert alert-danger mt-2 py-2">發生錯誤：${error.message}</div>`;
            console.error('API 請求失敗:', error);
        });
    }

// ---- 啟動 ----
window.addEventListener("DOMContentLoaded", () => {
  const mapEl = document.getElementById('map');
  const isLoggedIn = mapEl?.dataset.loggedIn === '1';
  const shouldShowReco = isLoggedIn && (mapEl?.dataset.autogeo === '0');

  if (shouldShowReco) {
    new bootstrap.Modal(document.getElementById('recoModal')).show();
  } else {
    // 保險起見：如果上一次還在 show，先關掉
    const inst = bootstrap.Modal.getInstance(document.getElementById('recoModal'));
    inst?.hide();
  }

  // 確認 → 存偏好 → 關 modal → 再 askGeo()
  document.getElementById('recoConfirm')?.addEventListener('click', async () => {
    const cats = [...document.querySelectorAll('input.reco-check:checked')].map(el => el.value);
    try {
      const resp = await fetch('/api/user/reco_prefs', {
        method: 'POST',
        headers: {'Content-Type':'application/json'},
        credentials: 'same-origin',
        body: JSON.stringify({ categories: cats })
      });
      const j = await resp.json().catch(()=>({}));
      if (!resp.ok || !j.ok) {
        alert('偏好儲存失敗：' + (j.error || resp.status));
        return;
      }
    } catch(e) {
      alert('網路錯誤，稍後再試');
      return;
    }
    bootstrap.Modal.getInstance(document.getElementById('recoModal'))?.hide();
    if (typeof askGeo === 'function') askGeo();
    renderAddressHistory(loadAddressHistory());
  });
  
  readCenterFromDataset();

  // 初始化地圖
  initMap(currentCenter, currentRadius, currentBrand);

  // 允許使用者變更位置（先試瀏覽器定位，不行再開選單）
  document.getElementById("changeLocBtn")?.addEventListener("click", () => showSelector());

  // 上方半徑「套用」：同步到後端並刷新
  document.getElementById("applyRadiusBtn")?.addEventListener("click", async () => {
    const r = parseFloat(document.getElementById("radiusInputTop")?.value || currentRadius);
    await postCenter(currentCenter.lat, currentCenter.lng, r);
  });

  // 品牌過濾：只更新地圖（若也要影響上方卡片，可加一個 /set_filter 再 reload）
  document.getElementById("brandSelect")?.addEventListener("change", (e) => {
    currentBrand = e.target.value || '';
    initMap(currentCenter, currentRadius, currentBrand);
    document.dispatchEvent(new Event("brand-or-location-changed"));
  });

  // 首次通知 spotlight 等元件
  document.dispatchEvent(new Event("brand-or-location-changed"));
});

// 不要有單獨的 `map` 殘留字樣
