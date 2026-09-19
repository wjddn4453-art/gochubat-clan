from __future__ import annotations

import asyncio, json, os, re, urllib.parse, urllib.request, urllib.error
from datetime import datetime, timedelta, timezone
from typing import Any, Optional

import discord
from discord import app_commands
from discord.ext import commands, tasks

# =========================================================
# GOCHUBAT CLAN v2 — simple clan / clan-match system
# Fresh rebuild. Old contracts, salary, FA, budget, transfers removed.
# =========================================================
TOKEN = os.getenv("CLAN_BOT_TOKEN", "").strip()
SUPABASE_URL = (os.getenv("CLAN_SUPABASE_URL") or os.getenv("SUPABASE_URL") or "").strip().rstrip("/")
SUPABASE_KEY = (os.getenv("CLAN_SUPABASE_KEY") or os.getenv("SUPABASE_SERVICE_ROLE_KEY") or os.getenv("SUPABASE_KEY") or "").strip()

COLOR = 0xC79A3B
GREEN = 0x3BA55D
RED = 0xED4245
BLUE = 0x5865F2
GRAY = 0x6B7280
KST = timezone(timedelta(hours=9))
MAX_MEMBERS = 8
MAX_ROSTER_SCORE = 150.0
APPLICATION_MINUTES = 60

ROLE_INACTIVE = 1549907420501905459   # 랭크 비활동 +3
ROLE_DOWN = 1538393520769867877       # 티어 하향 조정 -3
ROLE_UP = 1525960889239601252         # 티어 상향 조정 +5

POSITIONS = ["TOP", "JUG", "MID", "ADC", "SUP"]
POS_ALIASES = {"TOP":"TOP","탑":"TOP","JUG":"JUG","JG":"JUG","정글":"JUG","MID":"MID","미드":"MID","ADC":"ADC","AD":"ADC","원딜":"ADC","SUP":"SUP","서폿":"SUP","서포터":"SUP"}

# User-confirmed score table: TOP / JUG / MID / ADC / SUP
SCORE_ROWS = {
"GC2000+":[53.5,52.4,53.5,53.5,51.4],"GC1900-1999":[53.1,52.0,53.1,53.1,50.9],"GC1800-1899":[52.3,51.3,52.3,52.3,50.2],
"GC1700-1799":[51.7,50.6,51.7,51.7,49.5],"GC1600-1699":[50.9,49.9,50.9,50.9,48.8],"GC1500-1599":[50.2,49.1,50.2,50.2,48.0],
"GC1400-1499":[49.5,48.5,49.5,49.5,47.4],"GC1300-1399":[48.8,47.7,48.8,48.8,46.7],"GC1200-1299":[48.2,47.1,48.2,48.2,46.0],
"GC1100-1199":[47.4,46.3,47.4,47.4,45.3],"GC1000-1099":[46.7,45.6,46.7,46.7,44.5],"GC900-999":[46.0,44.9,46.0,46.0,43.9],
"GC800-899":[45.3,44.2,45.3,45.3,43.1],"GC700-799":[44.5,43.4,44.5,44.5,42.4],"GC600-699":[43.9,42.8,43.9,43.9,41.7],
"GC500-599":[43.1,42.1,43.1,43.1,41.0],"GC400-499":[42.5,41.4,42.5,42.5,40.3],"GC300-399":[41.7,40.7,41.7,41.7,39.6],
"GC200-299":[41.0,39.9,41.0,41.0,38.8],"GC100-199":[40.3,39.3,40.3,40.3,38.2],"GC0-99":[39.6,38.5,39.6,39.6,37.5],
"M1000+":[40.7,39.6,40.7,40.7,38.5],"M900-999":[40.1,39.1,40.1,40.1,38.0],"M800-899":[39.6,38.5,39.6,39.6,37.5],
"M700-799":[39.1,38.0,39.1,39.1,36.9],"M600-699":[38.0,36.9,38.0,38.0,35.8],"M500-599":[36.9,35.8,36.9,36.9,34.8],
"M400-499":[35.8,34.8,35.8,35.8,33.7],"M300-399":[35.1,34.0,35.1,35.1,33.0],"M200-299":[34.5,33.4,34.5,34.5,32.3],
"M100-199":[33.8,32.7,33.8,33.8,31.7],"M0-99":[33.2,32.1,33.2,33.2,31.0],
"D1":[31.0,30.5,32.1,30.0,31.6],"D2":[28.9,28.4,30.0,27.8,29.4],"D3":[26.8,26.2,27.8,25.7,27.3],"D4":[24.6,24.1,25.7,23.5,25.1],
"E1":[21.4,20.9,22.5,20.3,21.9],"E2":[19.3,18.7,20.3,18.2,19.8],"E3":[17.1,16.6,18.2,16.1,17.7],"E4":[15.0,14.4,16.1,13.9,15.5],
"P1":[12.8,12.3,13.9,11.8,13.4],"P2":[11.8,11.2,12.8,10.7,12.3],"P3":[10.7,10.2,11.8,9.6,11.2],"P4":[9.6,9.1,10.7,8.6,10.2],
"G1":[8.6,8.0,9.6,7.5,9.1],"G2":[7.5,7.0,8.6,6.4,8.0],"G3":[6.4,5.9,7.5,5.4,7.0],"G4":[5.4,4.8,6.4,4.3,5.9],
"S1":[4.3,4.0,4.8,3.7,4.6],"S2":[3.7,3.4,4.3,3.2,4.1],"S3":[3.2,2.9,3.7,2.7,3.5],"S4":[2.7,2.4,3.2,2.1,3.0],
"B1":[2.1,1.9,2.7,1.7,2.4],"B2":[1.8,1.6,2.4,1.4,2.0],"B3":[1.5,1.3,2.0,1.2,1.7],"B4":[1.2,1.0,1.7,1.0,1.4],
}


def utcnow(): return datetime.now(timezone.utc)
def iso(dt: datetime): return dt.astimezone(timezone.utc).isoformat()
def parse_dt(s):
    try: return datetime.fromisoformat(str(s).replace("Z", "+00:00")) if s else None
    except Exception: return None

def is_admin(m: discord.Member) -> bool: return bool(m.guild_permissions.administrator)

class DB:
    def __init__(self): self.base = SUPABASE_URL + "/rest/v1"; self.key = SUPABASE_KEY
    def _sync(self, method, path, payload=None, prefer=None):
        body = None if payload is None else json.dumps(payload, ensure_ascii=False).encode()
        h={"apikey":self.key,"Authorization":f"Bearer {self.key}","Content-Type":"application/json","Accept":"application/json"}
        if prefer: h["Prefer"] = prefer
        req=urllib.request.Request(self.base+"/"+path.lstrip("/"), data=body, headers=h, method=method)
        try:
            with urllib.request.urlopen(req, timeout=20) as r:
                raw=r.read().decode(); return json.loads(raw) if raw else []
        except urllib.error.HTTPError as e:
            raise RuntimeError(f"Supabase HTTP {e.code}: {e.read().decode(errors='replace')}")
    async def req(self,*a,**kw): return await asyncio.to_thread(self._sync,*a,**kw)
    async def select(self,t,q=""): return await self.req("GET", f"{t}?{q}" if q else t)
    async def insert(self,t,p): return await self.req("POST",t,p,"return=representation")
    async def update(self,t,q,p): return await self.req("PATCH",f"{t}?{q}",p,"return=representation")
    async def delete(self,t,q): return await self.req("DELETE",f"{t}?{q}",None,"return=representation")

db=DB()
def eq(v): return "eq."+urllib.parse.quote(str(v),safe="")

def tier_key_from_nick(nick: str) -> tuple[str,str]:
    # Nickname line info is deliberately ignored; only a slash-delimited tier token is used.
    parts=[p.strip().upper() for p in nick.split("/")]
    token=None
    for p in parts:
        if re.fullmatch(r"(?:GM|C|M)\d+|[DEPGSB][1-4]", p): token=p; break
    if not token: raise ValueError("닉네임에서 티어를 찾을 수 없습니다")
    if token.startswith("GM") or (token.startswith("C") and token[1:].isdigit()):
        lp=int(re.sub(r"\D","",token)); bucket="2000+" if lp>=2000 else f"{(lp//100)*100}-{(lp//100)*100+99}"
        return token, "GC"+bucket
    if token.startswith("M"):
        lp=int(token[1:]); bucket="1000+" if lp>=1000 else f"{(lp//100)*100}-{(lp//100)*100+99}"
        return token, "M"+bucket
    return token, token

def player_score(member: discord.Member, position: str):
    pos=POS_ALIASES.get(position.upper(), POS_ALIASES.get(position))
    if not pos: raise ValueError("포지션은 TOP/JUG/MID/ADC/SUP만 가능합니다")
    token,key=tier_key_from_nick(member.display_name)
    if key not in SCORE_ROWS: raise ValueError(f"지원하지 않는 티어입니다: {token}")
    base=SCORE_ROWS[key][POSITIONS.index(pos)]
    ids={r.id for r in member.roles}
    if ROLE_UP in ids and ROLE_DOWN in ids: raise ValueError("티어 상향 조정과 하향 조정 역할을 동시에 보유하고 있습니다")
    bonus=(5.0 if ROLE_UP in ids else 0.0)+(-3.0 if ROLE_DOWN in ids else 0.0)+(3.0 if ROLE_INACTIVE in ids else 0.0)
    return token, base, bonus, round(base+bonus,1)

intents=discord.Intents.default(); intents.members=True
bot=commands.Bot(command_prefix="!",intents=intents)
tree=bot.tree

async def send_ep(i,text,embed=None):
    if i.response.is_done(): await i.followup.send(text or None,embed=embed,ephemeral=True)
    else: await i.response.send_message(text or None,embed=embed,ephemeral=True)

async def active_clan_by_user(gid,uid):
    rows=await db.select("clan2_members",f"guild_id={eq(gid)}&user_id={eq(uid)}&is_active=eq.true&limit=1")
    if not rows:return None
    c=await db.select("clan2_clans",f"id={eq(rows[0]['clan_id'])}&is_active=eq.true&limit=1")
    return c[0] if c else None
async def clan_by_name(gid,name):
    r=await db.select("clan2_clans",f"guild_id={eq(gid)}&name={eq(name.strip())}&is_active=eq.true&limit=1"); return r[0] if r else None
async def clan_by_id(cid):
    r=await db.select("clan2_clans",f"id={eq(cid)}&limit=1"); return r[0] if r else None
async def membership(gid,uid):
    r=await db.select("clan2_members",f"guild_id={eq(gid)}&user_id={eq(uid)}&is_active=eq.true&limit=1"); return r[0] if r else None
async def members_of(cid): return await db.select("clan2_members",f"clan_id={eq(cid)}&is_active=eq.true&order=joined_at.asc")
async def can_manage(member,clan):
    if is_admin(member): return True
    m=await membership(member.guild.id,member.id)
    return bool(m and str(m['clan_id'])==str(clan['id']) and m['rank'] in ('leader','vice'))
async def leader_only(member,clan): return is_admin(member) or str(clan['leader_user_id'])==str(member.id)
async def log(guild,title,desc,color=COLOR):
    s=await db.select("clan2_settings",f"guild_id={eq(guild.id)}&limit=1")
    if not s or not s[0].get('log_channel_id'): return
    ch=guild.get_channel(int(s[0]['log_channel_id']))
    if ch:
        try: await ch.send(embed=discord.Embed(title=title,description=desc,color=color,timestamp=utcnow()))
        except Exception: pass

async def role_add(member,role_id):
    r=member.guild.get_role(int(role_id));
    if r: await member.add_roles(r,reason="클랜 시스템")
async def role_remove(member,role_id):
    r=member.guild.get_role(int(role_id));
    if r: await member.remove_roles(r,reason="클랜 시스템")

async def match_stats(gid):
    clans=await db.select("clan2_clans",f"guild_id={eq(gid)}&order=created_at.asc")
    matches=await db.select("clan2_matches",f"guild_id={eq(gid)}&status=eq.completed&order=completed_at.asc")
    st={str(c['id']):{'clan':c,'w':0,'l':0,'recent':[],'h2h':{},'streak':0,'best':0} for c in clans}
    for m in matches:
        a,b,w=str(m['clan_a_id']),str(m['clan_b_id']),str(m['winner_clan_id']); loser=b if w==a else a
        for cid,opp,won in ((w,loser,True),(loser,w,False)):
            if cid not in st: continue
            x=st[cid]; x['w' if won else 'l']+=1; x['recent'].append('W' if won else 'L')
            h=x['h2h'].setdefault(opp,[0,0]); h[0 if won else 1]+=1
            if won: x['streak']+=1; x['best']=max(x['best'],x['streak'])
            else: x['streak']=0
    return st

def rank_order(stats):
    # wins > win rate; head-to-head is applied only when the first two are tied.
    base=list(stats.values())
    def rate(x):
        g=x['w']+x['l']; return x['w']/g if g else 0
    base.sort(key=lambda x:(x['w'],rate(x)),reverse=True)
    # pairwise h2h tie-break for equal wins/rate. If h2h tied, stable/shared rank later.
    i=0
    while i<len(base):
        j=i+1
        while j<len(base) and base[j]['w']==base[i]['w'] and abs(rate(base[j])-rate(base[i]))<1e-12: j+=1
        if j-i==2:
            a,b=base[i],base[i+1]; h=a['h2h'].get(str(b['clan']['id']),[0,0])
            if h[1]>h[0]: base[i],base[i+1]=b,a
        i=j
    return base

@tree.command(name="클랜로그채널",description="[관리자] 클랜 시스템 로그 채널을 설정합니다.")
@app_commands.default_permissions(administrator=True)
async def set_log(i:discord.Interaction,채널:discord.TextChannel):
    if not is_admin(i.user): return await send_ep(i,"❌ Discord 관리자 권한이 필요합니다.")
    old=await db.select("clan2_settings",f"guild_id={eq(i.guild_id)}&limit=1")
    if old: await db.update("clan2_settings",f"guild_id={eq(i.guild_id)}",{"log_channel_id":str(채널.id),"updated_at":iso(utcnow())})
    else: await db.insert("clan2_settings",{"guild_id":str(i.guild_id),"log_channel_id":str(채널.id)})
    await send_ep(i,f"✅ 클랜 로그 채널을 {채널.mention}으로 설정했습니다.")

@tree.command(name="클랜생성",description="[관리자] 기존 Discord 역할을 연결해 새 클랜을 생성합니다.")
@app_commands.default_permissions(administrator=True)
async def create_clan(i:discord.Interaction,클랜명:str,클랜장:discord.Member,역할:discord.Role):
    if not is_admin(i.user): return await send_ep(i,"❌ Discord 관리자 권한이 필요합니다.")
    if await active_clan_by_user(i.guild_id,클랜장.id): return await send_ep(i,"❌ 해당 유저는 이미 다른 클랜에 소속되어 있습니다.")
    if await clan_by_name(i.guild_id,클랜명): return await send_ep(i,"❌ 현재 활동 중인 동일 이름 클랜이 있습니다.")
    used=await db.select("clan2_clans",f"guild_id={eq(i.guild_id)}&role_id={eq(역할.id)}&is_active=eq.true&limit=1")
    if used:return await send_ep(i,"❌ 해당 Discord 역할은 이미 다른 활동 클랜에 연결되어 있습니다.")
    c=(await db.insert("clan2_clans",{"guild_id":str(i.guild_id),"name":클랜명.strip(),"leader_user_id":str(클랜장.id),"role_id":str(역할.id),"created_by":str(i.user.id)}))[0]
    await db.insert("clan2_members",{"guild_id":str(i.guild_id),"clan_id":c['id'],"user_id":str(클랜장.id),"rank":"leader"})
    try: await role_add(클랜장,역할.id)
    except Exception as e: return await send_ep(i,f"⚠️ DB 생성은 완료됐지만 역할 지급에 실패했습니다: `{e}`\n봇 역할 위치를 확인한 뒤 `/클랜동기화`를 사용해주세요.")
    emb=discord.Embed(title="🏰 클랜 생성 완료",color=GREEN); emb.add_field(name="클랜",value=f"**{클랜명.strip()}**"); emb.add_field(name="클랜장",value=클랜장.mention); emb.add_field(name="연결 역할",value=역할.mention); emb.add_field(name="인원",value=f"1 / {MAX_MEMBERS}")
    await i.response.send_message(embed=emb); await log(i.guild,"🏰 클랜 생성",f"**{클랜명.strip()}** · 클랜장 {클랜장.mention} · 생성 {i.user.mention}",GREEN)

@tree.command(name="클랜초대",description="클랜장/부클랜장이 유저를 클랜에 초대합니다.")
async def invite(i:discord.Interaction,유저:discord.Member):
    c=await active_clan_by_user(i.guild_id,i.user.id)
    if not c or not await can_manage(i.user,c): return await send_ep(i,"❌ 클랜장 또는 부클랜장만 사용할 수 있습니다.")
    if await active_clan_by_user(i.guild_id,유저.id): return await send_ep(i,"❌ 해당 유저는 이미 클랜에 소속되어 있습니다.")
    if len(await members_of(c['id']))>=MAX_MEMBERS:return await send_ep(i,f"❌ 클랜 최대 인원은 {MAX_MEMBERS}명입니다.")
    inv=(await db.insert("clan2_invites",{"guild_id":str(i.guild_id),"clan_id":c['id'],"invitee_user_id":str(유저.id),"invited_by":str(i.user.id),"expires_at":iso(utcnow()+timedelta(hours=24))}))[0]
    v=discord.ui.View(timeout=None); v.add_item(discord.ui.Button(label="가입",emoji="✅",style=discord.ButtonStyle.success,custom_id=f"clan2:invite:yes:{inv['id']}")); v.add_item(discord.ui.Button(label="거절",emoji="❌",style=discord.ButtonStyle.danger,custom_id=f"clan2:invite:no:{inv['id']}"))
    emb=discord.Embed(title=f"🏰 {c['name']} 클랜 초대",description=f"{유저.mention}님을 **{c['name']}**에 초대했습니다.",color=COLOR)
    await i.response.send_message(content=유저.mention,embed=emb,view=v,allowed_mentions=discord.AllowedMentions(users=True))

@tree.command(name="클랜추방",description="클랜장/부클랜장이 클랜원을 추방합니다.")
async def kick(i:discord.Interaction,유저:discord.Member):
    c=await active_clan_by_user(i.guild_id,i.user.id)
    if not c or not await can_manage(i.user,c): return await send_ep(i,"❌ 클랜장 또는 부클랜장만 사용할 수 있습니다.")
    m=await membership(i.guild_id,유저.id)
    if not m or str(m['clan_id'])!=str(c['id']):return await send_ep(i,"❌ 해당 유저는 같은 클랜원이 아닙니다.")
    if m['rank']=='leader':return await send_ep(i,"❌ 클랜장은 추방할 수 없습니다.")
    me=await membership(i.guild_id,i.user.id)
    if me and me['rank']=='vice' and m['rank']=='vice':return await send_ep(i,"❌ 부클랜장은 다른 부클랜장을 추방할 수 없습니다.")
    await db.update("clan2_members",f"id={eq(m['id'])}",{"is_active":False,"left_at":iso(utcnow())})
    try: await role_remove(유저,c['role_id'])
    except Exception: pass
    await i.response.send_message(f"🚫 {유저.mention}님을 **{c['name']}**에서 추방했습니다."); await log(i.guild,"🚫 클랜원 추방",f"**{c['name']}** · {유저.mention} · 처리 {i.user.mention}",RED)

@tree.command(name="클랜탈퇴",description="현재 소속 클랜에서 탈퇴합니다.")
async def leave(i:discord.Interaction):
    m=await membership(i.guild_id,i.user.id)
    if not m:return await send_ep(i,"❌ 가입된 클랜이 없습니다.")
    if m['rank']=='leader':return await send_ep(i,"❌ 클랜장은 탈퇴할 수 없습니다. 클랜 해체 또는 관리자에게 문의해주세요.")
    c=await clan_by_id(m['clan_id']); await db.update("clan2_members",f"id={eq(m['id'])}",{"is_active":False,"left_at":iso(utcnow())})
    try: await role_remove(i.user,c['role_id'])
    except Exception: pass
    await i.response.send_message(f"🚪 **{c['name']}**에서 탈퇴했습니다.",ephemeral=True); await log(i.guild,"🚪 클랜 탈퇴",f"**{c['name']}** · {i.user.mention}")

@tree.command(name="부클랜장임명",description="클랜장이 클랜원 1명을 부클랜장으로 임명합니다.")
async def vice_set(i:discord.Interaction,유저:discord.Member):
    c=await active_clan_by_user(i.guild_id,i.user.id)
    if not c or not await leader_only(i.user,c) or (not is_admin(i.user) and str(c['leader_user_id'])!=str(i.user.id)):return await send_ep(i,"❌ 클랜장만 사용할 수 있습니다.")
    target=await membership(i.guild_id,유저.id)
    if not target or str(target['clan_id'])!=str(c['id']):return await send_ep(i,"❌ 같은 클랜원만 임명할 수 있습니다.")
    existing=await db.select("clan2_members",f"clan_id={eq(c['id'])}&rank=eq.vice&is_active=eq.true&limit=1")
    if existing:return await send_ep(i,"❌ 이미 부클랜장이 있습니다. 먼저 `/부클랜장해제`를 사용해주세요.")
    await db.update("clan2_members",f"id={eq(target['id'])}",{"rank":"vice"}); await i.response.send_message(f"🛡️ {유저.mention}님을 **{c['name']} 부클랜장**으로 임명했습니다."); await log(i.guild,"🛡️ 부클랜장 임명",f"**{c['name']}** · {유저.mention} · 처리 {i.user.mention}")

@tree.command(name="부클랜장해제",description="클랜장이 현재 부클랜장을 일반 클랜원으로 변경합니다.")
async def vice_unset(i:discord.Interaction):
    c=await active_clan_by_user(i.guild_id,i.user.id)
    if not c or str(c['leader_user_id'])!=str(i.user.id):return await send_ep(i,"❌ 클랜장만 사용할 수 있습니다.")
    r=await db.select("clan2_members",f"clan_id={eq(c['id'])}&rank=eq.vice&is_active=eq.true&limit=1")
    if not r:return await send_ep(i,"❌ 현재 부클랜장이 없습니다.")
    await db.update("clan2_members",f"id={eq(r[0]['id'])}",{"rank":"member"}); await i.response.send_message("✅ 부클랜장을 해제했습니다."); await log(i.guild,"🛡️ 부클랜장 해제",f"**{c['name']}** · <@{r[0]['user_id']}> · 처리 {i.user.mention}")

@tree.command(name="클랜목록",description="현재 활동 중인 클랜 목록을 확인합니다.")
async def clan_list(i:discord.Interaction):
    cs=await db.select("clan2_clans",f"guild_id={eq(i.guild_id)}&is_active=eq.true&order=created_at.asc")
    lines=[]
    for c in cs:
        ms=await members_of(c['id']); vice=next((m for m in ms if m['rank']=='vice'),None)
        vice_text = f"<@{vice['user_id']}>" if vice else "없음"
        lines.append(f"**{c['name']}** · 👑 <@{c['leader_user_id']}> · 🛡️ {vice_text} · 👥 {len(ms)}/{MAX_MEMBERS}")
    await i.response.send_message(embed=discord.Embed(title="🏰 고추밭 클랜 목록",description="\n".join(lines) if lines else "활동 중인 클랜이 없습니다.",color=COLOR))

@tree.command(name="클랜정보",description="클랜의 멤버와 누적 클랜전 기록을 확인합니다.")
async def clan_info(i:discord.Interaction,클랜명:str):
    c=await clan_by_name(i.guild_id,클랜명)
    if not c:return await send_ep(i,"❌ 해당 클랜을 찾을 수 없습니다.")
    ms=await members_of(c['id']); st=await match_stats(i.guild_id); x=st.get(str(c['id']),{'w':0,'l':0,'recent':[],'h2h':{},'streak':0,'best':0}); games=x['w']+x['l']; rate=x['w']/games*100 if games else 0
    vice=next((m for m in ms if m['rank']=='vice'),None); names=" · ".join(f"<@{m['user_id']}>" for m in ms)
    h=[]
    for oid,wl in x['h2h'].items():
        oc=await clan_by_id(oid)
        if oc:h.append(f"{oc['name']} · **{wl[0]}승 {wl[1]}패**")
    emb=discord.Embed(title=f"🏰 {c['name']}",color=COLOR); emb.add_field(name="👑 클랜장",value=f"<@{c['leader_user_id']}>"); emb.add_field(name="🛡️ 부클랜장",value=f"<@{vice['user_id']}>" if vice else "없음"); emb.add_field(name="👥 인원",value=f"{len(ms)} / {MAX_MEMBERS}"); emb.add_field(name="클랜원",value=names or "-",inline=False); emb.add_field(name="⚔️ 누적 전적",value=f"**{x['w']}승 {x['l']}패** · {rate:.1f}%"); emb.add_field(name="🔥 연승",value=f"현재 **{x['streak']}연승** · 최고 **{x['best']}연승**"); emb.add_field(name="최근 5경기",value=" ".join(x['recent'][-5:]) or "-",inline=False); emb.add_field(name="상대전적",value="\n".join(h) if h else "-",inline=False)
    await i.response.send_message(embed=emb)

@tree.command(name="클랜전신청",description="클랜장/부클랜장이 다른 클랜에 클랜전을 신청합니다.")
async def apply_match(i:discord.Interaction,상대클랜:str):
    a=await active_clan_by_user(i.guild_id,i.user.id)
    if not a or not await can_manage(i.user,a):return await send_ep(i,"❌ 클랜장 또는 부클랜장만 사용할 수 있습니다.")
    b=await clan_by_name(i.guild_id,상대클랜)
    if not b or str(a['id'])==str(b['id']):return await send_ep(i,"❌ 올바른 상대 클랜을 선택해주세요.")
    pending=await db.select("clan2_matches",f"guild_id={eq(i.guild_id)}&status=in.(pending,accepted,roster)&or=(and(clan_a_id.eq.{a['id']},clan_b_id.eq.{b['id']}),and(clan_a_id.eq.{b['id']},clan_b_id.eq.{a['id']}))&limit=1")
    if pending:return await send_ep(i,"❌ 두 클랜 사이에 이미 진행 중인 신청/클랜전이 있습니다.")
    exp=utcnow()+timedelta(minutes=APPLICATION_MINUTES)
    m=(await db.insert("clan2_matches",{"guild_id":str(i.guild_id),"clan_a_id":a['id'],"clan_b_id":b['id'],"requested_by":str(i.user.id),"status":"pending","request_expires_at":iso(exp),"channel_id":str(i.channel_id)}))[0]
    bms=await members_of(b['id']); mentions=[f"<@{b['leader_user_id']}>" ]+[f"<@{x['user_id']}>" for x in bms if x['rank']=='vice']
    v=discord.ui.View(timeout=None); v.add_item(discord.ui.Button(label="수락",emoji="⚔️",style=discord.ButtonStyle.success,custom_id=f"clan2:match:yes:{m['id']}")); v.add_item(discord.ui.Button(label="거절",emoji="❌",style=discord.ButtonStyle.danger,custom_id=f"clan2:match:no:{m['id']}"))
    emb=discord.Embed(title="⚔️ 클랜전 신청",description=f"**{a['name']}  VS  {b['name']}**\n\n상대 클랜장/부클랜장은 1시간 안에 수락 또는 거절해주세요.",color=BLUE); emb.add_field(name="신청자",value=i.user.mention); emb.add_field(name="만료",value=f"<t:{int(exp.timestamp())}:R>")
    await i.response.send_message(content=" ".join(mentions),embed=emb,view=v,allowed_mentions=discord.AllowedMentions(users=True)); msg=await i.original_response(); await db.update("clan2_matches",f"id={eq(m['id'])}",{"message_id":str(msg.id)}); await log(i.guild,"⚔️ 클랜전 신청",f"**{a['name']} VS {b['name']}** · 신청 {i.user.mention}",BLUE)

@tree.command(name="클랜전신청취소",description="클랜장/부클랜장이 아직 수락되지 않은 신청을 취소합니다.")
async def cancel_apply(i:discord.Interaction,상대클랜:str):
    a=await active_clan_by_user(i.guild_id,i.user.id); b=await clan_by_name(i.guild_id,상대클랜)
    if not a or not b or not await can_manage(i.user,a):return await send_ep(i,"❌ 처리할 수 없습니다.")
    r=await db.select("clan2_matches",f"guild_id={eq(i.guild_id)}&clan_a_id={eq(a['id'])}&clan_b_id={eq(b['id'])}&status=eq.pending&order=created_at.desc&limit=1")
    if not r:return await send_ep(i,"❌ 취소 가능한 신청이 없습니다.")
    await db.update("clan2_matches",f"id={eq(r[0]['id'])}",{"status":"cancelled","updated_at":iso(utcnow())}); await i.response.send_message(f"🚫 **{a['name']} VS {b['name']}** 클랜전 신청을 취소했습니다."); await log(i.guild,"🚫 클랜전 신청 취소",f"**{a['name']} VS {b['name']}** · 처리 {i.user.mention}",RED)

@tree.command(name="클랜전로스터",description="수락된 클랜전의 TOP/JUG/MID/ADC/SUP 로스터를 구성합니다.")
async def roster(i:discord.Interaction,상대클랜:str,탑:discord.Member,정글:discord.Member,미드:discord.Member,원딜:discord.Member,서폿:discord.Member):
    c=await active_clan_by_user(i.guild_id,i.user.id); opp=await clan_by_name(i.guild_id,상대클랜)
    if not c or not opp or not await can_manage(i.user,c):return await send_ep(i,"❌ 클랜장 또는 부클랜장만 사용할 수 있습니다.")
    r=await db.select("clan2_matches",f"guild_id={eq(i.guild_id)}&status=in.(accepted,roster)&or=(and(clan_a_id.eq.{c['id']},clan_b_id.eq.{opp['id']}),and(clan_a_id.eq.{opp['id']},clan_b_id.eq.{c['id']}))&order=created_at.desc&limit=1")
    if not r:return await send_ep(i,"❌ 로스터를 등록할 수 있는 클랜전이 없습니다.")
    match=r[0]; existing=await db.select("clan2_rosters",f"match_id={eq(match['id'])}&clan_id={eq(c['id'])}&limit=1")
    if existing and existing[0]['is_locked']:return await send_ep(i,"❌ 이미 확정된 로스터입니다. 변경하려면 관리자에게 확정 해제를 요청해주세요.")
    players=[탑,정글,미드,원딜,서폿]
    if len({x.id for x in players})!=5:return await send_ep(i,"❌ 서로 다른 클랜원 5명을 선택해야 합니다.")
    cids={str(x['user_id']) for x in await members_of(c['id'])}
    if any(str(x.id) not in cids for x in players):return await send_ep(i,"❌ 출전 선수 5명 모두 현재 자기 클랜원이어야 합니다.")
    details=[]; total=0.0
    try:
        for p,pos in zip(players,POSITIONS):
            token,base,bonus,final=player_score(p,pos); total+=final; details.append({"position":pos,"user_id":str(p.id),"tier":token,"base":base,"bonus":bonus,"score":final})
    except ValueError as e:return await send_ep(i,f"❌ 로스터 계산 실패: {e}")
    total=round(total,1)
    payload={"guild_id":str(i.guild_id),"match_id":match['id'],"clan_id":c['id'],"players":details,"total_score":total,"is_locked":False,"updated_by":str(i.user.id),"updated_at":iso(utcnow())}
    if existing: await db.update("clan2_rosters",f"id={eq(existing[0]['id'])}",payload)
    else: await db.insert("clan2_rosters",payload)
    lines=[]
    for d in details:
        bonus_text = f" ({d['bonus']:+.1f})" if d['bonus'] else ""
        lines.append(f"**{d['position']}** <@{d['user_id']}> · `{d['tier']}` · {d['base']:.1f}{bonus_text} → **{d['score']:.1f}**")
    emb=discord.Embed(title=f"📋 {c['name']} 로스터",description="\n".join(lines),color=GREEN if total<=MAX_ROSTER_SCORE else RED); emb.add_field(name="TEAM SCORE",value=f"**{total:.1f} / {MAX_ROSTER_SCORE:.1f}**",inline=False)
    if total<=MAX_ROSTER_SCORE:
        v=discord.ui.View(timeout=None); v.add_item(discord.ui.Button(label="로스터 확정",emoji="🔒",style=discord.ButtonStyle.success,custom_id=f"clan2:roster:lock:{match['id']}:{c['id']}")); emb.set_footer(text="확정 전까지 /클랜전로스터로 자유롭게 수정할 수 있습니다."); await i.response.send_message(embed=emb,view=v,ephemeral=True)
    else:
        emb.set_footer(text=f"제한 점수를 {total-MAX_ROSTER_SCORE:.1f}점 초과하여 확정할 수 없습니다."); await i.response.send_message(embed=emb,ephemeral=True)

async def reveal_rosters(guild,match):
    rs=await db.select("clan2_rosters",f"match_id={eq(match['id'])}&is_locked=eq.true")
    if len(rs)<2:return None
    a,b=await clan_by_id(match['clan_a_id']),await clan_by_id(match['clan_b_id']); by={str(x['clan_id']):x for x in rs}
    def block(c):
        r=by[str(c['id'])]; lines=[f"**{d['position']}** <@{d['user_id']}> · `{d['tier']}` · **{d['score']:.1f}**" for d in r['players']]; return f"### {c['name']}\n"+"\n".join(lines)+f"\n**TOTAL {float(r['total_score']):.1f} / 150.0**"
    return discord.Embed(title="⚔️ CLAN MATCH · 로스터 확정",description=block(a)+"\n\n**VS**\n\n"+block(b),color=COLOR)

@tree.command(name="로스터확정해제",description="[관리자] 확정된 클랜전 로스터를 다시 수정 가능 상태로 돌립니다.")
@app_commands.default_permissions(administrator=True)
async def roster_unlock(i:discord.Interaction,클랜명:str,상대클랜:str):
    if not is_admin(i.user):return await send_ep(i,"❌ Discord 관리자 권한이 필요합니다.")
    c=await clan_by_name(i.guild_id,클랜명); o=await clan_by_name(i.guild_id,상대클랜)
    if not c or not o:return await send_ep(i,"❌ 클랜을 찾을 수 없습니다.")
    ms=await db.select("clan2_matches",f"guild_id={eq(i.guild_id)}&status=in.(accepted,roster,ready)&or=(and(clan_a_id.eq.{c['id']},clan_b_id.eq.{o['id']}),and(clan_a_id.eq.{o['id']},clan_b_id.eq.{c['id']}))&order=created_at.desc&limit=1")
    if not ms:return await send_ep(i,"❌ 대상 클랜전을 찾을 수 없습니다.")
    await db.update("clan2_rosters",f"match_id={eq(ms[0]['id'])}&clan_id={eq(c['id'])}",{"is_locked":False,"updated_at":iso(utcnow())}); await db.update("clan2_matches",f"id={eq(ms[0]['id'])}",{"status":"roster","updated_at":iso(utcnow())}); await i.response.send_message(f"🔓 **{c['name']}** 로스터 확정을 해제했습니다."); await log(i.guild,"🔓 로스터 확정 해제",f"**{c['name']} VS {o['name']}** · 처리 {i.user.mention}")

@tree.command(name="클랜전결과",description="[관리자] 확정된 클랜전 결과와 스코어를 등록합니다.")
@app_commands.default_permissions(administrator=True)
async def result(i:discord.Interaction,클랜1:str,클랜2:str,승리클랜:str,클랜1스코어:app_commands.Range[int,0,99],클랜2스코어:app_commands.Range[int,0,99]):
    if not is_admin(i.user):return await send_ep(i,"❌ Discord 관리자 권한이 필요합니다.")
    a,b=await clan_by_name(i.guild_id,클랜1),await clan_by_name(i.guild_id,클랜2); w=await clan_by_name(i.guild_id,승리클랜)
    if not a or not b or not w or str(w['id']) not in {str(a['id']),str(b['id'])}:return await send_ep(i,"❌ 클랜 선택을 확인해주세요.")
    if 클랜1스코어==클랜2스코어:return await send_ep(i,"❌ 무승부는 지원하지 않습니다.")
    actual=a if 클랜1스코어>클랜2스코어 else b
    if str(actual['id'])!=str(w['id']):return await send_ep(i,"❌ 입력한 스코어와 승리 클랜이 일치하지 않습니다.")
    ms=await db.select("clan2_matches",f"guild_id={eq(i.guild_id)}&status=eq.ready&or=(and(clan_a_id.eq.{a['id']},clan_b_id.eq.{b['id']}),and(clan_a_id.eq.{b['id']},clan_b_id.eq.{a['id']}))&order=created_at.desc&limit=1")
    if not ms:return await send_ep(i,"❌ 양쪽 로스터가 확정된 대상 클랜전이 없습니다.")
    m=ms[0]; sa=클랜1스코어 if str(m['clan_a_id'])==str(a['id']) else 클랜2스코어; sb=클랜2스코어 if str(m['clan_b_id'])==str(b['id']) else 클랜1스코어
    await db.update("clan2_matches",f"id={eq(m['id'])}",{"status":"completed","winner_clan_id":w['id'],"score_a":sa,"score_b":sb,"completed_at":iso(utcnow()),"result_by":str(i.user.id),"updated_at":iso(utcnow())}); await i.response.send_message(embed=discord.Embed(title="🏆 클랜전 결과",description=f"**{클랜1} {클랜1스코어} : {클랜2스코어} {클랜2}**\n\nWINNER · **{승리클랜}**",color=GREEN)); await log(i.guild,"🏆 클랜전 결과",f"**{클랜1} {클랜1스코어} : {클랜2스코어} {클랜2}** · 승리 **{승리클랜}** · 등록 {i.user.mention}",GREEN)

@tree.command(name="클랜전결과수정",description="[관리자] 완료된 클랜전의 승자와 스코어를 수정합니다.")
@app_commands.default_permissions(administrator=True)
async def result_edit(i:discord.Interaction,경기번호:str,승리클랜:str,A스코어:app_commands.Range[int,0,99],B스코어:app_commands.Range[int,0,99]):
    if not is_admin(i.user):return await send_ep(i,"❌ Discord 관리자 권한이 필요합니다.")
    r=await db.select("clan2_matches",f"id={eq(경기번호)}&guild_id={eq(i.guild_id)}&status=eq.completed&limit=1")
    if not r:return await send_ep(i,"❌ 완료된 경기번호를 찾을 수 없습니다.")
    m=r[0]; w=await clan_by_name(i.guild_id,승리클랜)
    if not w or str(w['id']) not in {str(m['clan_a_id']),str(m['clan_b_id'])} or A스코어==B스코어:return await send_ep(i,"❌ 승리 클랜/스코어를 확인해주세요.")
    expected=str(m['clan_a_id']) if A스코어>B스코어 else str(m['clan_b_id'])
    if str(w['id'])!=expected:return await send_ep(i,"❌ 스코어와 승리 클랜이 일치하지 않습니다.")
    await db.update("clan2_matches",f"id={eq(m['id'])}",{"winner_clan_id":w['id'],"score_a":A스코어,"score_b":B스코어,"result_by":str(i.user.id),"updated_at":iso(utcnow())}); await send_ep(i,"✅ 결과를 수정했습니다. 순위/연승/상대전적은 완료 경기 원본에서 다시 계산되므로 자동 반영됩니다."); await log(i.guild,"🛠️ 클랜전 결과 수정",f"경기 `{m['id']}` · 처리 {i.user.mention}")

@tree.command(name="클랜전결과취소",description="[관리자] 완료된 경기 결과를 취소해 전적 집계에서 제외합니다.")
@app_commands.default_permissions(administrator=True)
async def result_cancel(i:discord.Interaction,경기번호:str):
    if not is_admin(i.user):return await send_ep(i,"❌ Discord 관리자 권한이 필요합니다.")
    r=await db.select("clan2_matches",f"id={eq(경기번호)}&guild_id={eq(i.guild_id)}&status=eq.completed&limit=1")
    if not r:return await send_ep(i,"❌ 완료된 경기번호를 찾을 수 없습니다.")
    await db.update("clan2_matches",f"id={eq(경기번호)}",{"status":"result_cancelled","updated_at":iso(utcnow())}); await send_ep(i,"✅ 해당 결과를 취소했습니다. 누적 전적에서 자동 제외됩니다."); await log(i.guild,"↩️ 클랜전 결과 취소",f"경기 `{경기번호}` · 처리 {i.user.mention}",RED)

@tree.command(name="클랜전취소",description="[관리자] 수락 후 진행 중인 클랜전을 전적 반영 없이 취소합니다.")
@app_commands.default_permissions(administrator=True)
async def match_cancel(i:discord.Interaction,클랜1:str,클랜2:str):
    if not is_admin(i.user):return await send_ep(i,"❌ Discord 관리자 권한이 필요합니다.")
    a,b=await clan_by_name(i.guild_id,클랜1),await clan_by_name(i.guild_id,클랜2)
    if not a or not b:return await send_ep(i,"❌ 클랜을 찾을 수 없습니다.")
    r=await db.select("clan2_matches",f"guild_id={eq(i.guild_id)}&status=in.(accepted,roster,ready)&or=(and(clan_a_id.eq.{a['id']},clan_b_id.eq.{b['id']}),and(clan_a_id.eq.{b['id']},clan_b_id.eq.{a['id']}))&order=created_at.desc&limit=1")
    if not r:return await send_ep(i,"❌ 진행 중인 클랜전이 없습니다.")
    await db.update("clan2_matches",f"id={eq(r[0]['id'])}",{"status":"cancelled","updated_at":iso(utcnow())}); await i.response.send_message(f"🚫 **{클랜1} VS {클랜2}** 클랜전을 취소했습니다."); await log(i.guild,"🚫 클랜전 취소",f"**{클랜1} VS {클랜2}** · 처리 {i.user.mention}",RED)

@tree.command(name="클랜순위",description="누적 승리 수 → 승률 → 상대전적 기준 클랜 순위를 확인합니다.")
async def ranking(i:discord.Interaction):
    st=await match_stats(i.guild_id); ordered=rank_order(st); lines=[]; prev=None; rank=0
    for idx,x in enumerate(ordered,1):
        g=x['w']+x['l']; rate=x['w']/g*100 if g else 0; key=(x['w'],round(rate,10));
        if key!=prev: rank=idx
        prev=key; lines.append(f"**{rank}위 · {x['clan']['name']}** — **{x['w']}승 {x['l']}패** · {rate:.1f}%")
    emb=discord.Embed(title="🏆 고추밭 클랜 순위",description="\n".join(lines) if lines else "등록된 클랜이 없습니다.",color=COLOR); emb.set_footer(text="기준: 누적 승리 수 → 승률 → 상대전적 · 시즌 초기화 없음")
    await i.response.send_message(embed=emb)

@tree.command(name="클랜기록",description="역대 누적 클랜전 기록을 확인합니다.")
async def records(i:discord.Interaction):
    st=await match_stats(i.guild_id)
    if not st:return await i.response.send_message("아직 클랜 기록이 없습니다.")
    wins=max(st.values(),key=lambda x:x['w']); best=max(st.values(),key=lambda x:x['best']); games=max(st.values(),key=lambda x:x['w']+x['l'])
    emb=discord.Embed(title="🏅 고추밭 클랜 기록",color=COLOR); emb.add_field(name="⚔️ 최다 승리",value=f"**{wins['clan']['name']} · {wins['w']}승**",inline=False); emb.add_field(name="🔥 최고 연승",value=f"**{best['clan']['name']} · {best['best']}연승**",inline=False); emb.add_field(name="🎮 최다 경기",value=f"**{games['clan']['name']} · {games['w']+games['l']}경기**",inline=False); await i.response.send_message(embed=emb)

@tree.command(name="클랜해체",description="클랜장 또는 관리자가 클랜을 해체합니다.")
async def dissolve(i:discord.Interaction,클랜명:Optional[str]=None):
    c=await clan_by_name(i.guild_id,클랜명) if 클랜명 else await active_clan_by_user(i.guild_id,i.user.id)
    if not c or not (is_admin(i.user) or str(c['leader_user_id'])==str(i.user.id)):return await send_ep(i,"❌ 해당 클랜의 클랜장 또는 Discord 관리자만 사용할 수 있습니다.")
    active=await db.select("clan2_matches",f"guild_id={eq(i.guild_id)}&status=in.(accepted,roster,ready)&or=(clan_a_id.eq.{c['id']},clan_b_id.eq.{c['id']})&limit=1")
    if active:return await send_ep(i,"❌ 진행 중인 클랜전이 있습니다. 관리자가 `/클랜전취소` 후 해체해주세요.")
    v=discord.ui.View(timeout=None); v.add_item(discord.ui.Button(label="정말 해체",emoji="⚠️",style=discord.ButtonStyle.danger,custom_id=f"clan2:dissolve:{c['id']}"))
    await i.response.send_message(embed=discord.Embed(title="⚠️ 클랜 해체",description=f"정말 **{c['name']}**을 해체하시겠습니까?\n클랜 역할은 전원 회수되며 과거 전적은 보존됩니다.",color=RED),view=v,ephemeral=True)

@tree.command(name="클랜동기화",description="[관리자] DB 소속을 기준으로 클랜 Discord 역할을 동기화합니다.")
@app_commands.default_permissions(administrator=True)
async def sync_roles(i:discord.Interaction):
    if not is_admin(i.user):return await send_ep(i,"❌ Discord 관리자 권한이 필요합니다.")
    await i.response.defer(ephemeral=True); cs=await db.select("clan2_clans",f"guild_id={eq(i.guild_id)}&is_active=eq.true"); changed=0
    active_map={}
    for c in cs:
        for m in await members_of(c['id']): active_map[str(m['user_id'])]=str(c['role_id'])
    clan_role_ids={int(c['role_id']) for c in cs}
    for member in i.guild.members:
        wanted=active_map.get(str(member.id)); have={r.id for r in member.roles}
        for rid in clan_role_ids:
            if rid in have and str(rid)!=wanted:
                try: await role_remove(member,rid); changed+=1
                except Exception: pass
        if wanted and int(wanted) not in have:
            try: await role_add(member,wanted); changed+=1
            except Exception: pass
    await i.followup.send(f"✅ 클랜 역할 동기화 완료 · 변경 {changed}건",ephemeral=True)

@tree.command(name="클랜도움말",description="클랜 시스템 명령어와 규칙을 확인합니다.")
async def help_cmd(i:discord.Interaction):
    emb=discord.Embed(title="🏰 고추밭 클랜 시스템",description="친목 클랜 + 누적 클랜전 기록 시스템",color=COLOR)
    emb.add_field(name="클랜",value="`/클랜목록` `/클랜정보` `/클랜초대` `/클랜추방` `/클랜탈퇴`\n`/부클랜장임명` `/부클랜장해제`",inline=False)
    emb.add_field(name="클랜전",value="`/클랜전신청` `/클랜전신청취소` `/클랜전로스터` `/클랜순위` `/클랜기록`",inline=False)
    emb.add_field(name="로스터 규칙",value="5명 · TOP/JUG/MID/ADC/SUP 1명씩 · 닉네임에서 티어만 읽음 · 닉네임 라인은 무시 · 150.0점 이하만 확정",inline=False)
    emb.add_field(name="점수 보정",value="티어 상향 +5 · 티어 하향 -3 · 랭크 비활동 +3\n상향+비활동 +8 / 하향+비활동 0 / 상향+하향 동시 보유는 확정 불가",inline=False)
    await i.response.send_message(embed=emb,ephemeral=True)

async def handle_component(i:discord.Interaction):
    cid=(i.data or {}).get('custom_id','')
    if not cid.startswith('clan2:'): return
    parts=cid.split(':')
    try:
        if parts[1]=='invite':
            invs=await db.select('clan2_invites',f"id={eq(parts[3])}&status=eq.pending&limit=1")
            if not invs:return await send_ep(i,"❌ 이미 처리된 초대입니다.")
            inv=invs[0]
            if str(i.user.id)!=str(inv['invitee_user_id']):return await send_ep(i,"❌ 초대받은 본인만 처리할 수 있습니다.")
            if parse_dt(inv['expires_at'])<utcnow(): await db.update('clan2_invites',f"id={eq(inv['id'])}",{'status':'expired'}); return await send_ep(i,"❌ 만료된 초대입니다.")
            if parts[2]=='no': await db.update('clan2_invites',f"id={eq(inv['id'])}",{'status':'rejected'}); return await i.response.edit_message(content="❌ 클랜 초대를 거절했습니다.",embed=None,view=None)
            c=await clan_by_id(inv['clan_id'])
            if await active_clan_by_user(i.guild_id,i.user.id):return await send_ep(i,"❌ 이미 다른 클랜에 소속되어 있습니다.")
            if len(await members_of(c['id']))>=MAX_MEMBERS:return await send_ep(i,"❌ 클랜 인원이 가득 찼습니다.")
            await db.insert('clan2_members',{'guild_id':str(i.guild_id),'clan_id':c['id'],'user_id':str(i.user.id),'rank':'member'}); await db.update('clan2_invites',f"id={eq(inv['id'])}",{'status':'accepted'}); await role_add(i.user,c['role_id']); await i.response.edit_message(content=f"✅ {i.user.mention}님이 **{c['name']}**에 가입했습니다.",embed=None,view=None); await log(i.guild,"👤 클랜 가입",f"**{c['name']}** · {i.user.mention} · 초대 <@{inv['invited_by']}>",GREEN)
        elif parts[1]=='match':
            ms=await db.select('clan2_matches',f"id={eq(parts[3])}&status=eq.pending&limit=1")
            if not ms:return await send_ep(i,"❌ 이미 처리된 신청입니다.")
            m=ms[0]; b=await clan_by_id(m['clan_b_id'])
            if not await can_manage(i.user,b):return await send_ep(i,"❌ 상대 클랜의 클랜장 또는 부클랜장만 처리할 수 있습니다.")
            if parse_dt(m['request_expires_at'])<utcnow(): await db.update('clan2_matches',f"id={eq(m['id'])}",{'status':'expired'}); return await i.response.edit_message(content="⏰ 1시간이 지나 클랜전 신청이 만료되었습니다.",embed=None,view=None)
            a=await clan_by_id(m['clan_a_id'])
            if parts[2]=='no': await db.update('clan2_matches',f"id={eq(m['id'])}",{'status':'rejected','responded_by':str(i.user.id),'updated_at':iso(utcnow())}); await i.response.edit_message(content=f"❌ **{a['name']} VS {b['name']}** 신청이 거절되었습니다.",embed=None,view=None); await log(i.guild,"❌ 클랜전 신청 거절",f"**{a['name']} VS {b['name']}** · 처리 {i.user.mention}",RED); return
            await db.update('clan2_matches',f"id={eq(m['id'])}",{'status':'accepted','responded_by':str(i.user.id),'accepted_at':iso(utcnow()),'updated_at':iso(utcnow())}); await i.response.edit_message(content=f"✅ **{a['name']} VS {b['name']}** 클랜전 신청이 수락되었습니다.\n양쪽 클랜장/부클랜장은 `/클랜전로스터`를 구성해주세요.",embed=None,view=None); await log(i.guild,"✅ 클랜전 신청 수락",f"**{a['name']} VS {b['name']}** · 처리 {i.user.mention}",GREEN)
        elif parts[1]=='roster' and parts[2]=='lock':
            mid,clanid=parts[3],parts[4]; c=await clan_by_id(clanid)
            if not await can_manage(i.user,c):return await send_ep(i,"❌ 해당 클랜의 클랜장/부클랜장만 확정할 수 있습니다.")
            rs=await db.select('clan2_rosters',f"match_id={eq(mid)}&clan_id={eq(clanid)}&limit=1")
            if not rs:return await send_ep(i,"❌ 저장된 로스터가 없습니다.")
            if float(rs[0]['total_score'])>MAX_ROSTER_SCORE:return await send_ep(i,"❌ 150점을 초과한 로스터는 확정할 수 없습니다.")
            await db.update('clan2_rosters',f"id={eq(rs[0]['id'])}",{'is_locked':True,'locked_at':iso(utcnow())}); allr=await db.select('clan2_rosters',f"match_id={eq(mid)}&is_locked=eq.true")
            if len(allr)>=2:
                await db.update('clan2_matches',f"id={eq(mid)}",{'status':'ready','updated_at':iso(utcnow())}); m=(await db.select('clan2_matches',f"id={eq(mid)}&limit=1"))[0]; emb=await reveal_rosters(i.guild,m); await i.response.edit_message(content="✅ 양 팀 로스터가 모두 확정되었습니다.",embed=emb,view=None); await log(i.guild,"📋 양 팀 로스터 확정",emb.description if emb else f"경기 {mid}",GREEN)
            else:
                await db.update('clan2_matches',f"id={eq(mid)}",{'status':'roster','updated_at':iso(utcnow())}); await i.response.edit_message(content="🔒 로스터를 확정했습니다. 상대 클랜의 확정을 기다리고 있습니다.\n상대 로스터는 양쪽 모두 확정될 때 동시에 공개됩니다.",embed=None,view=None); await log(i.guild,"🔒 로스터 확정",f"**{c['name']}** · 총점 **{float(rs[0]['total_score']):.1f}/150.0** · 확정 {i.user.mention}")
        elif parts[1]=='dissolve':
            c=await clan_by_id(parts[2])
            if not c or not c['is_active'] or not (is_admin(i.user) or str(c['leader_user_id'])==str(i.user.id)):return await send_ep(i,"❌ 처리 권한이 없습니다.")
            active=await db.select('clan2_matches',f"guild_id={eq(i.guild_id)}&status=in.(accepted,roster,ready)&or=(clan_a_id.eq.{c['id']},clan_b_id.eq.{c['id']})&limit=1")
            if active:return await send_ep(i,"❌ 진행 중인 클랜전이 있어 해체할 수 없습니다.")
            ms=await members_of(c['id'])
            for x in ms:
                mem=i.guild.get_member(int(x['user_id']))
                if mem:
                    try: await role_remove(mem,c['role_id'])
                    except Exception: pass
            await db.update('clan2_members',f"clan_id={eq(c['id'])}&is_active=eq.true",{'is_active':False,'left_at':iso(utcnow())}); await db.update('clan2_clans',f"id={eq(c['id'])}",{'is_active':False,'dissolved_at':iso(utcnow()),'dissolved_by':str(i.user.id)}); await i.response.edit_message(content=f"💥 **{c['name']}** 클랜을 해체했습니다. 과거 전적은 보존됩니다.",embed=None,view=None); await log(i.guild,"💥 클랜 해체",f"**{c['name']}** · 처리 {i.user.mention}",RED)
    except Exception as e:
        await send_ep(i,f"❌ 처리 중 오류가 발생했습니다: `{e}`")

@bot.event
async def on_interaction(i:discord.Interaction):
    if i.type==discord.InteractionType.component and str((i.data or {}).get('custom_id','')).startswith('clan2:'):
        await handle_component(i)

@tasks.loop(minutes=1)
async def expire_loop():
    now=iso(utcnow())
    for g in bot.guilds:
        rows=await db.select('clan2_matches',f"guild_id={eq(g.id)}&status=eq.pending&request_expires_at=lt.{urllib.parse.quote(now,safe='')}")
        for m in rows:
            await db.update('clan2_matches',f"id={eq(m['id'])}",{'status':'expired','updated_at':now})
            ch=g.get_channel(int(m['channel_id'])) if m.get('channel_id') else None
            if ch and m.get('message_id'):
                try:
                    msg=await ch.fetch_message(int(m['message_id'])); await msg.edit(content="⏰ 1시간 동안 응답이 없어 클랜전 신청이 만료되었습니다.",embed=None,view=None)
                except Exception: pass

@bot.event
async def on_ready():
    if not expire_loop.is_running(): expire_loop.start()
    print(f"[CLAN v2] 로그인: {bot.user} / guilds={len(bot.guilds)}")

class ClanBot(commands.Bot):
    async def setup_hook(self):
        await self.tree.sync()
        print(f"[CLAN v2] 슬래시 명령어 동기화 완료: {len(self.tree.get_commands())}개")

# setup_hook is patched onto the already-created bot to preserve the simple construction above.
async def _setup_hook():
    await tree.sync(); print(f"[CLAN v2] 슬래시 명령어 동기화 완료: {len(tree.get_commands())}개")
bot.setup_hook=_setup_hook

if __name__=="__main__":
    if not TOKEN: raise RuntimeError("CLAN_BOT_TOKEN 환경변수가 없습니다.")
    if not SUPABASE_URL or not SUPABASE_KEY: raise RuntimeError("CLAN_SUPABASE_URL / CLAN_SUPABASE_KEY 환경변수를 확인해주세요.")
    bot.run(TOKEN)
