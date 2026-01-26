"""
Import menu data from exported file
"""
import asyncio
import json
from motor.motor_asyncio import AsyncIOMotorClient
import os
from dotenv import load_dotenv
from pathlib import Path
import uuid

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

mongo_url = os.environ['MONGO_URL']
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ['DB_NAME']]

# Menu data from export
MENU_DATA = [
  {
    "category": "Завтраки до 16.00",
    "dishes": [
      {"name": "Сырники со сметаной и соусом \"Розмариновая вишня\"", "description": "Воздушные творожные шарики с вишнево-розмариновым соусом", "price": "15", "weight": "250гр", "image": "https://ik.imagekit.io/lunchpad/1qsm08p0yplveu3g650h7qof86psb2f6_UsMKarknL"},
      {"name": "Овсянка со сливочным сыром", "description": "Овсяная каша с сыром", "price": "12", "weight": "200/30", "image": "https://ik.imagekit.io/lunchpad/ny4ryxoruj3r7nxriquro9lkehmyi8sn_cCiI5uxU6"},
      {"name": "Гранола с сезонными фруктами", "description": "Злаковый микс, с Греческий йогуртом, сливками и фруктами", "price": "17", "weight": "200", "image": "https://ik.imagekit.io/lunchpad/j4jb3vg9op45gdpfyedgfovgg6e5mkxz_NBKfrp3VR"},
      {"name": "Крок мадам", "description": "Тост с беконом, яйцом и соусом на основе плавленного сыра", "price": "18", "weight": "400", "image": "https://ik.imagekit.io/lunchpad/2wydnhu6b8rfu4ohppxnphtddltd7c56_GPwqj3ezK"},
      {"name": "Авокадо тост с лососем", "price": "27", "weight": "210", "image": "https://ik.imagekit.io/lunchpad/2svnp8ekvdnoza3ecqua93rj21jo6skc_ahcprsnZf"},
      {"name": "Тост с индейкой и тар таром из огурца", "price": "22", "weight": "210", "image": "https://ik.imagekit.io/lunchpad/gcdqw4qu1ej32yu2je8dpmiga5pyqai7_Kbye3ewb2"},
      {"name": "Тост с хумусом и скрэмблом", "price": "22", "weight": "210", "image": "https://ik.imagekit.io/lunchpad/u6xqqgkdqc1y4lbhwggpaagrv6nwt8ut_vbG4OfEt7"},
      {"name": "Омлет базилик с чипосоусом", "price": "17", "weight": "250", "image": "https://ik.imagekit.io/lunchpad/qo4vt62296ogmszbo4mibnttm076mhlh_-W1W0yrce"},
      {"name": "Омлет с сыром Пармезан", "description": "Классический омлет с сыром Пармезан и хлебом", "price": "17", "weight": "200", "image": "https://ik.imagekit.io/lunchpad/wqqclhayotpb5e7xxfnp1q9pt7y2crkc_RI5WzmC4L"},
      {"name": "Шакшука", "price": "17", "weight": "320 гр", "image": "https://ik.imagekit.io/lunchpad/n1vi17m0q4nw9d1l6lmftsuobwul0sfi_-kDPJKZG2"},
      {"name": "Пицца по-домашнему", "price": "21", "weight": "380гр", "image": "https://ik.imagekit.io/lunchpad/s9x27r7pmnhng6jim61apdrkxs9ah1eb_JTBraSUHT"},
      {"name": "Фриттата с беконом и пармезаном", "price": "17", "weight": "210гр", "image": "https://ik.imagekit.io/lunchpad/0grwrfw16w1nyqee5nc02xjxrott0j2n_sO3FtViME"},
      {"name": "Драник с лососем и соусом огурец", "price": "28", "weight": "240гр", "image": "https://ik.imagekit.io/lunchpad/mbv1ts9mrsc3u7cussp8xruif1mvvlxz_bbOw87q4S"},
      {"name": "Вегетарианский бургер", "description": "Бургер с яйцом, свежим томатом и огурцом", "price": "11", "weight": "250гр", "image": "https://ik.imagekit.io/lunchpad/qn0mcai7bg0x3u881qiwg2zjp7xsgpbm_RHc9TtgnH"}
    ]
  },
  {
    "category": "Сезонное меню",
    "dishes": [
      {"name": "Карпаччо из свеклы", "description": "Слайсы отварной свеклы с каперсами и селедкой", "price": "15", "weight": "150гр", "image": "https://ik.imagekit.io/lunchpad/2wfnfw5866fopcp27yxv97dy2g3hw710_A3KBL3we1"},
      {"name": "Суп пюре из тыквы с креветками", "description": "Воздушный тыквенный мусс на основе кокосового молока с креветками и семенами льна", "price": "15", "weight": "300гр", "image": "https://ik.imagekit.io/lunchpad/8pwjyyjm3cw641jb6vioggmvy6u5an8d_BdGaf31hA"},
      {"name": "Тыква с уткой конфи и луковым мармеладом", "description": "Утка конфи с тыквой и луковым мармеладом в соусе демиглас", "price": "26", "weight": "200гр", "image": "https://ik.imagekit.io/lunchpad/umrj7xf3xu1wnd105trm47q12giqc1ow_ugU0NxA4W"},
      {"name": "Тыквенный маффин с ванильным мороженым", "description": "Сезонный десерт с шариком пломбира", "price": "10", "weight": "150/50", "image": "https://ik.imagekit.io/lunchpad/zkckn3xmm4b200h1ma4jflkgzoxbzz21_eYBl40R05"},
      {"name": "Холодник", "price": "9.5", "weight": "300гр", "image": "https://ik.imagekit.io/lunchpad/uzd1tuzm9awrfgvb9gbs708q8hpv2cwv_hD9-n6DAP"},
      {"name": "Летний салат", "description": "Легкий салат с арбузом, сыром Фета, красным луком и томатами Черри", "price": "16.5", "weight": "270", "image": "https://ik.imagekit.io/lunchpad/qybo7mtcf4003ul8nh4ui1860senzp85_bCeuZ1eLg"},
      {"name": "Гаспачо", "description": "Испанский холодный суп с креветками, миндалём и стружкой наполеона", "price": "9.5", "weight": "240гр", "image": "https://ik.imagekit.io/lunchpad/qct27o1zisyyjyhp6bm11zr5ktlahcqg_jVxcXnyTg"}
    ]
  },
  {
    "category": "Суши и роллы",
    "dishes": [
      {"name": "Хосо сет", "description": "Сет мини роллов с креветкой, тунцом, лососем, огурцом и авокадо", "price": "47", "weight": "550", "image": "https://ik.imagekit.io/lunchpad/xth1reyljxu6r53mn9blv0hi8ap52t60_Vs22FzVkdJ"},
      {"name": "Сет №1", "description": "Классический сет из Филадельфии, Калифорнии, Бонито", "price": "70", "weight": "645гр", "image": "https://ik.imagekit.io/lunchpad/g7t5fg3xvg9x2jus099z7va72w3zv9d4_oP1RsvyPS"},
      {"name": "Сет №2", "description": "Массу магуро, Эби урамаки, Филадельфия с чука салатом, ролл с опаленным тунцом", "price": "85", "weight": "1200гр", "image": "https://ik.imagekit.io/lunchpad/v9qoq3rmovtrjwvadbkgnlrcrxf2wjed_l4SrNELwC"},
      {"name": "Сет №3", "description": "Филадельфия классическая, Бонито, Ролл с тунцом, Ролл с ростбифом", "price": "110", "weight": "1500гр", "image": "https://ik.imagekit.io/lunchpad/2pcz903d6siwmkmoamdve21yfzqwy197_6G-ZA8t5B"},
      {"name": "Ролл с опаленным тунцом", "description": "Тунец, рис, фисташки, огурец, такуан, сливочный сыр, соус Спайси", "price": "22", "weight": "220", "image": "https://ik.imagekit.io/lunchpad/ey3nv1arjztwtm6ozx84kf3sc1e17i5i_-oq-UmrYc"},
      {"name": "Теплый ролл с лососем терияки", "description": "Лосось терияки, рис, креметта", "price": "22", "weight": "300гр", "image": "https://ik.imagekit.io/lunchpad/9tm8junsyxtjkcya2tt1z0bqo3uhl49r_GeFraK6Re"},
      {"name": "Филадельфия Классическая", "description": "Лосось, рис, сливочный сыр", "price": "26", "weight": "230гр", "image": "https://ik.imagekit.io/lunchpad/bzyw6uqww7z98o15jvqxkv2i9mcbc3p4_x3RBDIZyz"},
      {"name": "Калифорния", "description": "Креветка, рис, икра летучей рыбы, авокадо, огурец", "price": "24", "weight": "215гр", "image": "https://ik.imagekit.io/lunchpad/r2o42wjxkcxvoc4bm06ih4q1rgzuf1zi_aQ3VyCO3K"},
      {"name": "Бонито", "description": "Лосось, рис, авокадо, огурец, сливочный сыр, стружка тунца", "price": "24", "weight": "200гр", "image": "https://ik.imagekit.io/lunchpad/k5ngpe0v3wlsv5uls2gik9498weerp2y_N86CX0R8n"}
    ]
  },
  {
    "category": "Салаты",
    "dishes": [
      {"name": "Зеленый салат с кунжутным соусом", "description": "Сочетание салатных листьев и брокколи с авокадо, огурца, соевых бобов", "price": "22", "weight": "280гр", "image": "https://ik.imagekit.io/lunchpad/hxp1yucxuvrg1am7lkayr7q4sgp5mki8_JUzWbF7Fyr"},
      {"name": "Стейк салат с соусом чимичурри", "description": "Салат с говядиной, томатом, луком и огурцом", "price": "27", "weight": "330 гр", "image": "https://ik.imagekit.io/lunchpad/eveuc9rqsb97ugz0hop59mfhxcqo0mqu_C-1_A7Ckj"},
      {"name": "Салат с индейкой", "description": "Свежие листья салата, сельдерей, редис Дайкон, слайсы из филе Индейки", "price": "28", "weight": "280", "image": "https://ik.imagekit.io/lunchpad/44mfks0g0e7wg0q3x31do0xortasvc3c_oHdcuN1Kv"},
      {"name": "Салат «Цезарь» с куриным филе", "description": "Микс салат, соус «цезарь», томат черри, перепелиное яйцо, куриное филе", "price": "24", "weight": "210гр", "image": "https://ik.imagekit.io/lunchpad/dd4hj984nnf2kwv5kjy4u6b9x2e38204_v2ybCbBPH"},
      {"name": "Салат «Цезарь» с креветками", "description": "Микс салат, соус «цезарь», томат черри, перепелиное яйцо, креветки", "price": "29", "weight": "210гр", "image": "https://ik.imagekit.io/lunchpad/alp9o5vi3axhgk8vu563kf70ao8hbewi_YJ4jcCuV8"},
      {"name": "Салат Греческий", "description": "Томат, огурец, болгарский перец, сыр Фета, оливки и маслины под соусом Песто", "price": "20", "weight": "210гр", "image": "https://ik.imagekit.io/lunchpad/77kfg4z262edthglsdnj3fk4hl78e07e_Cm52t1Fn8"}
    ]
  },
  {
    "category": "Закуски",
    "dishes": [
      {"name": "Запеченные мидии с красной икрой", "description": "Количесвто мидий 4-6шт", "price": "25", "weight": "160гр", "image": "https://ik.imagekit.io/lunchpad/1pfe2z2k1nqsx51zzqe3zmqfxstihhrp_FvukFL-4B"},
      {"name": "Карпаччо из говядины", "description": "Говядина вырезка, сыр, томат черри, острая заправка", "price": "30", "weight": "110/70 гр", "image": "https://ik.imagekit.io/lunchpad/0j532lfe6glrep7jjebdd7k7f4l7dkqu__RYp82qix"},
      {"name": "Тар-тар из говядины", "description": "Классический тар-тар из говядины", "price": "30", "weight": "200 гр", "image": "https://ik.imagekit.io/lunchpad/e3zxwmjzy4pdjo0qpxi1ktqoq0btkrve_milzpUeVl"},
      {"name": "Хумус с тунцом", "description": "Слайсы маринованного тунца на подушке из хумуса", "price": "28", "weight": "340гр", "image": "https://ik.imagekit.io/lunchpad/875uywk52q66m6foe9ibttqqgoaju5zb_XDobRcc6M"},
      {"name": "Боул с лососем и кус кусом", "description": "Нежный лосось на подушке из кус-куса, с перцем терияки", "price": "31", "weight": "300 гр", "image": "https://ik.imagekit.io/lunchpad/bkz5setls2fuf8k6x7bze2nfck007ss3_HP_Z6DlE1"},
      {"name": "Креветки в азиатском стиле", "description": "Королевские креветки, обжаренные на чесночном масле", "price": "32", "weight": "150гр", "image": "https://ik.imagekit.io/lunchpad/co39izorrh18dp8fnymali5rpwndjhkm_gMVCIDQMt"},
      {"name": "Куриные стрипсы", "description": "Пряные стрипсы из куриного филе с соусом сладкий чили", "price": "22", "weight": "250/100", "image": "https://ik.imagekit.io/lunchpad/rtq9m3e0el2f3vftqsk0iczr32xmpom2_-XONDZK0M"},
      {"name": "Тар-тар из лосося", "description": "Измельченный лосось со сливочным сыром и лимонной заправкой", "price": "24.5", "weight": "90/40/40/20", "image": "https://ik.imagekit.io/lunchpad/olddgewjs83tw3u7ymf4chq3y0fw8co0_oxMkcsIlg"},
      {"name": "Сет брускетт", "description": "С ростбифом, с лососем и томатом черри", "price": "25", "weight": "3шт / 180гр", "image": "https://ik.imagekit.io/lunchpad/vt6xh2fy0e7s0v8shmrwhtsztj51l6zb_JbRh3m3rL"}
    ]
  },
  {
    "category": "Бургеры и Сэндвичи",
    "dishes": [
      {"name": "Бургер с индейкой", "description": "Булочка, микс салат, котлета из индейки, бекон, сыр Чеддер", "price": "32", "weight": "500гр", "image": "https://ik.imagekit.io/lunchpad/6k5658o5n7ntm7e0jfu80d78j60iuso5_8esjjYEKB"},
      {"name": "Фиш бургер с лососем Терияки", "description": "Булочка, микс салат, лосось терияки, сыр Чеддер, бекон", "price": "32", "weight": "500гр", "image": "https://ik.imagekit.io/lunchpad/ffkayo1144yd1b80tjoz8iwlxruxbhsy_LNY0tX5OBj"},
      {"name": "Чизбургер с вишневым соусом", "description": "Булочка, микс салат, котлета из свинины и говядины, вишневый соус", "price": "28", "weight": "500гр", "image": "https://ik.imagekit.io/lunchpad/mrwncmcti4na9c3xrvsf6u1lz8ueov53_hhRJVM28N"},
      {"name": "Гамбургер с грибным соусом", "description": "Булочка, микс салат, котлета из говядины, бекон, грибной соус", "price": "32", "weight": "500гр", "image": "https://ik.imagekit.io/lunchpad/rzdbpoqrdm2xkiivz9jsnuumfvn8wygp_RgR73Cny4"},
      {"name": "Сэндвич с куриным филе и беконом на гриле", "description": "Микс салат, томат, филе цыпленка, бекон, сыр Чеддер", "price": "26", "weight": "350 гр", "image": "https://ik.imagekit.io/lunchpad/ou7ismahrko0hyk1dpp760mj5rvtbmh6_qxL6bdWXz"}
    ]
  },
  {
    "category": "Супы",
    "dishes": [
      {"name": "Холодник с перепелиным яйцом и картофелем", "description": "Холодник на кефире, с зеленью и перепелиным яйцом", "price": "14", "weight": "450гр", "image": "https://ik.imagekit.io/lunchpad/hocmj4znl89h2aayy94tctlfoe8d79os_oyfqPQsA4"},
      {"name": "Уха на бревне", "description": "Суп из двух видов рыбы, готовится на щепе", "price": "17", "weight": "400гр", "image": "https://ik.imagekit.io/lunchpad/5zhgbu0k8nr1z2mm77vcp4rh6d4za1fe_NmVDV3TmQ"},
      {"name": "Борщ с ростбифом", "description": "Борщ с ростбифом, бородинским хлебом, шпиком, маринованным чесноком", "price": "17", "weight": "450гр", "image": "https://ik.imagekit.io/lunchpad/iuhm3qsaqff1xa3jz996f5lfk93prwtt_uVbk8HzAJ"},
      {"name": "Суп Чаудер", "description": "Сливочный суп из морепродуктов с беконом", "price": "22", "weight": "400гр", "image": "https://ik.imagekit.io/lunchpad/vepccevbhf9ewzd0fk3df5l3am5sfml7_mJdNo8HIu"},
      {"name": "Томатный суп с морепродуктами", "description": "Суп из измельченных томатов с лососем, креветками", "price": "17.5", "weight": "250", "image": "https://ik.imagekit.io/lunchpad/hbleytzhq3l44lejn6epr5w3nvhlwddj_QqMMlsw_M"}
    ]
  },
  {
    "category": "Паста",
    "dishes": [
      {"name": "Паста карбонара", "description": "Паста, бекон, яйцо, сливки, сыр грано падано", "price": "25", "weight": "220гр", "image": "https://ik.imagekit.io/lunchpad/0z6a718h5ad85xhn763ln2nwbzqe2lvq_I_plo3uuz"},
      {"name": "Паста с цыпленком в стиле WOK", "description": "Паста в азиатском стиле в соусе с добавлением меда", "price": "24", "weight": "360", "image": "https://ik.imagekit.io/lunchpad/6bqw4zn3ltfme4o2a1wdwykb7d1p98fp_-ucniv92m"},
      {"name": "Паста с тунцом и каперсами", "description": "Паста с тунцом, каперсами и томатом черри", "price": "28", "weight": "290", "image": "https://ik.imagekit.io/lunchpad/18y4cb38s3o6vfugxdg0tzt1meyn0cbl_cpgBdr413N"},
      {"name": "Паста с цыпленком и соусом из томатов", "description": "Паста с филе цыпленка, измельченными томатами", "price": "22", "weight": "320", "image": "https://ik.imagekit.io/lunchpad/nqjxvhd82lwqt99ui45x4te7rnkijby3_rKqSEdPqa"}
    ]
  },
  {
    "category": "Горячие блюда",
    "dishes": [
      {"name": "Стейк Ри-Бай (100гр)", "description": "Наиболее известный стейк в мире. Средний вес стейка 300гр", "price": "18", "weight": "100 гр", "image": "https://ik.imagekit.io/lunchpad/lzut9j67817trwgkmye763q7bdjuusuj_DvlKzQEqi"},
      {"name": "Соте из цыпленка в кокосовом соусе", "description": "Куриное филе с перцем под соусом на основе кокосового молока", "price": "28", "weight": "400 гр", "image": "https://ik.imagekit.io/lunchpad/mjog1zkfs5hdfgzyzyddpreaamze3743_lIjbjpW8a"},
      {"name": "Цыпленок в горчичном соусе с картофельным пюре", "description": "Цыпленок в горчичном соусе с нежным картофельным пюре", "price": "31", "weight": "320 гр", "image": "https://ik.imagekit.io/lunchpad/adwgdf8in2nr29udxp8mzaoyvgrvu0vt_irmaUgw6S"},
      {"name": "Стейк из свинины с картофельным гратеном", "price": "37", "weight": "350 гр", "image": "https://ik.imagekit.io/lunchpad/qkvr5cdpm7b7gks9elreiwumxb6wtlu0_ewJmoLsA7c"},
      {"name": "Утиная ножка с картофельным пюре", "price": "42", "weight": "320 гр", "image": "https://ik.imagekit.io/lunchpad/4uwvcq8gyzp0v6udf2xldaoja6548ofs_seg-vgx4T2"},
      {"name": "Стейк из говядины с пюре и соусом Демиглас", "description": "Стейк из говядины, приготовленный по технологии су-вид", "price": "48", "weight": "370 гр", "image": "https://ik.imagekit.io/lunchpad/iuerrxzhniyqtmmlmr657z89402d8qjb_ko3DG8o72"},
      {"name": "Обожженный лосось с соусом Ромеско", "description": "Нежное филе лосося с кабачками", "price": "47", "weight": "250 гр", "image": "https://ik.imagekit.io/lunchpad/5zkqx58ufih1mni775ppuu9je2vpc16h_EFOguqHmq"}
    ]
  },
  {
    "category": "Десерты",
    "dishes": [
      {"name": "Десерт Рафаэлло", "price": "14", "image": "https://ik.imagekit.io/lunchpad/5tu1zo6885bgoglb1xv6polvvpdxjy7m_btvYUvhtD"},
      {"name": "Десерт Павлова", "description": "Десерт украшается сезонными фруктами/ягодами", "price": "12", "image": "https://ik.imagekit.io/lunchpad/0a6bm8tmjnze7l2snpt56hgibeubpo50_CDcOu8UVN"},
      {"name": "Наполеон", "description": "Десерт украшается сезонными фруктами/ягодами", "price": "14", "image": "https://ik.imagekit.io/lunchpad/5bvhkmxpqs0o5706q9up3uap4xo76pv4_vR8Mpxs38"},
      {"name": "Сливочный чизкейк", "price": "14", "image": "https://ik.imagekit.io/lunchpad/8t00g9dh5nk106b0xk3clkugrc18nc0p_CfEiWSekcS"},
      {"name": "Медовик шоколадный", "price": "14", "image": "https://ik.imagekit.io/lunchpad/oz0xpvw3ityf9ltwvfnob7f6sgqul0bp_xZSkJyWyK"},
      {"name": "Карамельный чизкейк", "price": "14", "image": "https://ik.imagekit.io/lunchpad/y6jjmtu6okacd7b5btpqfkub1a978ptl_I_PnGoTpl"},
      {"name": "Брауни с пломбиром", "price": "14", "weight": "80/50", "image": "https://ik.imagekit.io/lunchpad/3ig7hf23kqpcidmvz6a246j7bddf0kb5_iBoJZE02M"},
      {"name": "Мороженое", "price": "8", "image": "https://ik.imagekit.io/lunchpad/tyst3bn57ln9j96yo14kfbtrxoidcrts_oTIeXgLqp"}
    ]
  },
  {
    "category": "Лимонады",
    "dishes": [
      {"name": "Киви Бонг", "description": "Киви, сироп зелёного яблока, газировка", "price": "12", "weight": "250мл", "image": "https://ik.imagekit.io/lunchpad/2sz7klwdpwhywzzrhhatzs1jkscj8cgd_S6K9dHX7C"},
      {"name": "Лимонад Черника-Лаванда", "price": "12", "weight": "250мл", "image": "https://ik.imagekit.io/lunchpad/fp02i050tf2xyy0ychujgjwsi5rzuqa4_ogCcwY9TZ"},
      {"name": "Пряный ананас", "description": "Ананас, пряный сироп, вода", "price": "12", "weight": "250мл", "image": "https://ik.imagekit.io/lunchpad/cqphmjsfjfuxpoidxt6jtt5ugp5j779l_sdt_Iii0z"},
      {"name": "Лимонад Малина-кокос", "price": "12", "weight": "250мл", "image": "https://ik.imagekit.io/lunchpad/wacugknvtk92b8tynbrc1qaayzzpzsp8_3hETTwLij"},
      {"name": "Огуречный лимонад", "description": "Огурец, яблочный сок, лимон, Sprite", "price": "12", "weight": "250мл", "image": "https://ik.imagekit.io/lunchpad/k0arsp8wjcrezr50xv17kxssg6kn4cvy_900kLZD_l"},
      {"name": "Лимонад Маракуя-Чиа", "price": "12", "weight": "250 мл", "image": "https://ik.imagekit.io/lunchpad/6dodupw4mynbehtzt9zki5ua0mz16o3q__8N_5rxES"}
    ]
  },
  {
    "category": "Кальяны",
    "dishes": [
      {"name": "Simple", "price": "38", "image": "https://ik.imagekit.io/lunchpad/Q3P6CMavtKZyfkcZIjNqHWSwuBg1_lam3mf6wybg6_3zRQVFyGz.jpg"},
      {"name": "Premium", "price": "47", "image": "https://ik.imagekit.io/lunchpad/Q3P6CMavtKZyfkcZIjNqHWSwuBg1_aoa725sdeg8w_Srjs578JLR.jpg"},
      {"name": "Fruit", "price": "65", "image": "https://ik.imagekit.io/lunchpad/Q3P6CMavtKZyfkcZIjNqHWSwuBg1_34guec3wl7ry_7rqUxRVBNi.jpg"},
      {"name": "Special", "price": "59", "image": "https://ik.imagekit.io/lunchpad/Q3P6CMavtKZyfkcZIjNqHWSwuBg1_ekfkidw1kfwz__Xjw3LG4o.jpg"},
      {"name": "Chef", "price": "59", "image": "https://ik.imagekit.io/lunchpad/Q3P6CMavtKZyfkcZIjNqHWSwuBg1_i0rthr08djhb_7ieF9hIOB.jpg"}
    ]
  }
]

async def import_menu():
    # Delete existing categories and menu items
    await db.categories.delete_many({})
    await db.menu_items.delete_many({})
    
    print("Importing menu data...")
    
    for sort_order, category_data in enumerate(MENU_DATA, start=1):
        # Create category
        category_id = str(uuid.uuid4())
        category = {
            "id": category_id,
            "name": category_data["category"],
            "sort_order": sort_order,
            "is_active": True
        }
        await db.categories.insert_one(category)
        print(f"Created category: {category_data['category']}")
        
        # Create menu items
        for item_order, dish in enumerate(category_data["dishes"], start=1):
            price_str = dish.get("price", "0")
            try:
                price = float(price_str)
            except:
                price = 0.0
            
            menu_item = {
                "id": str(uuid.uuid4()),
                "category_id": category_id,
                "name": dish["name"],
                "description": dish.get("description", ""),
                "price": price,
                "weight": dish.get("weight", ""),
                "image_url": dish.get("image", ""),
                "is_available": True,
                "is_business_lunch": False,
                "is_promotion": False,
                "is_hit": item_order <= 2,  # Mark first 2 items as hits
                "is_new": item_order == 3 if len(category_data["dishes"]) > 3 else False,
                "is_spicy": False,
                "sort_order": item_order
            }
            await db.menu_items.insert_one(menu_item)
        
        print(f"  Added {len(category_data['dishes'])} items")
    
    print("\nMenu import completed!")
    
    # Count totals
    categories_count = await db.categories.count_documents({})
    items_count = await db.menu_items.count_documents({})
    print(f"Total categories: {categories_count}")
    print(f"Total menu items: {items_count}")

if __name__ == "__main__":
    asyncio.run(import_menu())
