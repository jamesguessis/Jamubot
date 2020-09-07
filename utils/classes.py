from datetime import datetime, timedelta
from discord import Embed
import ujson

class Json(object):
  '''Reimplement dict as json to have helper functions builtin'''
  def __init__(self, d):
    self.s = d

  def __setitem__(self, k, v):
    self.s[k] = v
  
  def __getitem__(self, k):
    return Json(self.s[k]) if type(self.s[k]) == dict else self.s[k]

  def __delitem__(self, k):
    if k in self.s:
      self.s.remove(k)
    else:
      raise KeyError('Key {} doesn\'t exist'.format(k))

  def __contains__(self, k):
    return k in self.s

  def __len__(self):
    return len(self.s)

  def __iterkv__(self):
    for k in self.s:
      yield Json(k) if type(k) == dict else k

  def __iter__(self):
    for k in self.__iterkv__():
      yield k

  def keys(self):
    return self.__iter__()

  def values(self):
    for k in self.__iterkv__():
      yield k

  def items(self):
    return self.__iterkv__()

  def get(self, k):
    if k in self.s:
      return Json(self.s[k]) if type(self.s[k]) == dict else self.s[k]
    else:
      return None

  def __str__(self):
    # beatmap is not JSON serializable
    tmp = self.s.copy()
    if 'bmap' in tmp:
      del tmp['bmap']
    return ujson.dumps(tmp)

  def __repr__(self):
    return self.__str__()

  # start of helper functions
  def parse_stamp(self):
    diff = datetime.utcnow() - datetime.strptime(self['created_at'].split('+')[0], '%Y-%m-%dT%H:%M:%S')
    diff = datetime(1,1,1) + diff
    ago = []
    if (t:=diff.year-1) != 0:
      ago.append(f'{t} y')
    if (t:=diff.month-1) != 0:
      ago.append(f'{t} mo')
    if (t:=diff.day-1) != 0:
      ago.append(f'{t} d')
    if (t:=diff.hour) != 0:
      ago.append(f'{t} h')
    if (t:=diff.minute) != 0:
      ago.append(f'{t} m')
    ago.append(f'{diff.second} s')
    return ' '.join(ago)

  @property
  def get_rank(self):
    ranks = {
      'A': '<:A_:752671985192140820>',
      'B': '<:B_:752671985267638334>',
      'C': '<:C_:752671985179557988>',
      'D': '<:D_:752671985242341427>',
      'F': '<:F_:752671985196072990>',
      'S': '<:S_:752671984873373780>',
      'SS': '<:SS:752671985225433229>',
      'SH': '<:SH:752671985213112431>',
      'SSH': '<:SSH:752671985242341466>'
    }
    return ranks[self['rank']]
  
  @property
  def get_status(self):
    statuses = {
      'ranked': '<:ranked:752671985045340201>',
      'qualified': '<:qualified:752671985171038299>',
      'loved': '<:loved:752671985175232583>',
    }
    if (s:= self['beatmap']['status']) in statuses:
      return statuses[s]
    else:
      return '<:unranked:752671984990552096>'

  @property
  def get_pp(self):
    # We can assume that the required data already exists here because it's being called at all
    return self['bmap'].getPP(
      ''.join(self['mods']),
      n300 = self['statistics']['count_300'],
      n100 = self['statistics']['count_100'],
      n50 = self['statistics']['count_50'],
      misses = self['statistics']['count_miss'],
      combo = self['max_combo'],
      recalculate = True
    ).total_pp

  @property
  def get_fc(self):
    # Same as get_pp
    return self['bmap'].getPP(
      ''.join(self['mods']),
      n300 = self['statistics']['count_300']\
        + self['statistics']['count_miss'],
      n100 = self['statistics']['count_100'],
      n50 = self['statistics']['count_50'],
      misses = 0, combo = self['bmap'].maxCombo(),
      recalculate = True
    ).total_pp

class User(Json):
  @property
  def playtime_str(self):
    t = 'Play time: '
    mins, secs = divmod(self['statistics']['play_time'], 60)
    hrs, mins = divmod(mins, 60)
    days, hrs = divmod(hrs, 24)
    yrs, days = divmod(days, 365)
    if yrs > 0: t += f'{yrs}y '
    if days > 0: t += f'{days}d '
    if hrs > 0: t += f'{hrs}h '
    if mins > 0: t += f'{mins}m '
    if secs > 0: t += f'{secs}s'
    return t

  @property
  def as_embed(self):
    e = Embed(description=f'''
    **Rank:** #{self['statistics']['rank']['global']} ({self['country_code']}#{self['statistics']['rank']['country']})
    **Total PP:** {self['statistics']['pp']:.2f}
    **Level:** {self['statistics']['level']['current']} ({self['statistics']['level']['progress'] / 100:.2f})
    **Accuracy:** {self['statistics']['hit_accuracy']:.2f}
    **Playcount:** {self['statistics']['play_count']}
    ''', colour=0x00FFC0)
    e.set_author(
      name=f"{self['playmode']} profile for {self['username']}",
      icon_url=f"https://osu.ppy.sh/images/flags/{self['country_code']}.png",
      url=f"https://osu.ppy.sh/users/{self['id']}"
    )
    e.set_thumbnail(url=self['avatar_url'])
    e.set_footer(text=self.playtime_str)
    return e

class Recent(Json):
  @property
  def completion(self):
    '''This is here because recent is the only thing that will have fails'''
    num = (self['statistics']['count_300'] + self['statistics']['count_100'] +
       self['statistics']['count_50'] + self['statistics']['count_miss'])
    first = self['bmap'].hitobjects[0].starttime
    current = self['bmap'].hitobjects[num - 1].starttime
    if self['bmap'].hitobjects[-1].osu_obj == 1<<0: # Circle
      last = self['bmap'].hitobjects[-1].starttime
    elif self['bmap'].hitobjects[-1].osu_obj == 1<<1: # Slider
      inherited = self['bmap'].slider_multiplier
      for t in self['bmap'].timingpoints:
        if t.change >= 0:
          inherited = t.change
          bl = t.change
        else: bl = inherited * abs(t.change / 100)
        if t.starttime >= self['bmap'].hitobjects[-1].starttime: break
      d = self['bmap'].hitobjects[-1].distance / (self['bmap'].slider_multiplier * 100) * bl
      last = self['bmap'].hitobjects[-1].starttime + d * self['bmap'].hitobjects[-1].repetitions
    elif self['bmap'].hitobjects[-1].osu_obj == 1<<3: # Spinner
      last = self['bmap'].hitobjects[-1].endtime
    return (current - first) / (last - first)

  @property
  def as_embed(self):
    mods = ''.join(self['mods']) if len(self['mods']) > 0 else 'NM'
    n300 = self['statistics']['count_300']
    n100 = self['statistics']['count_100']
    n50 = self['statistics']['count_50']
    miss = self['statistics']['count_miss']
    pp = f'{self.get_pp:.2f}PP' if self['beatmap']['ranked'] == 1 and self['rank'] != 'F' else f'~~{self.get_pp:.2f}PP~~'
    fc = f'{self.get_fc:.2f}PP' if self['beatmap']['ranked'] == 1 and self['rank'] != 'F' else f'~~{self.get_fc:.2f}PP~~'
    e = Embed(description=f'''
    {self.get_status} **[{self['beatmapset']['artist']} - {self['beatmapset']['title']}[{self['beatmap']['version']}]]({self['beatmap']['url']}) +{mods}**
    {self.get_rank} **{pp}** x{self['max_combo']}/{self['bmap'].maxCombo()} {self['accuracy'] * 100:.2f}%
    {self['score']} [{n100}/{n50}/{miss}] {self['beatmap']['difficulty_rating']:.2f}★
    {f'{self.completion * 100:.2f}% completion' if self['rank'] == 'F' else f'{self.parse_stamp()} ago'}
    {f"{fc} for {self['bmap'].getPP().getAccFromValues(n300 + miss, n100, n50, 0) * 100:.2f}% FC" if self['max_combo'] != self['bmap'].maxCombo() else ''}''', colour=0x00FFC0)
    e.set_thumbnail(url=f"https://b.ppy.sh/thumb/{self['beatmapset']['id']}l.jpg")
    e.set_author(
      name=f"recent {self['mode']} plays for {self['user']['username']}",
      icon_url=f"https://osu.ppy.sh/images/flags/{self['user']['country_code']}.png",
      url=f"https://osu.ppy.sh/users/{self['user']['id']}"
    )
    return e

class Best(Json):
  @property
  def as_embed(self):
    des = []
    for i, s in enumerate(self):
      mods = ''.join(s['mods']) if len(s['mods']) > 0 else 'nomod'
      n300 = s['statistics']['count_300']
      n100 = s['statistics']['count_100']
      n50 = s['statistics']['count_50']
      miss = s['statistics']['count_miss']
      des.append(f'''
      **{i+1}. [{s['beatmapset']['artist']} - {s['beatmapset']['title']}[{s['beatmap']['version']}]]({s['beatmap']['url']}) +{mods}**
      {s.get_rank} **{s.get_pp:.2f}PP** {s['max_combo']}/{s['bmap'].maxCombo()} {s['accuracy'] * 100:.2f}%
      {s['score']} [{n100}/{n50}/{miss}] {s['beatmap']['difficulty_rating']:.2f}★
      {s.parse_stamp()} ago
      {f"{s.get_fc}PP for {s['bmap'].getPP().getAccFromValues(n300 + miss, n100, n50, 0) * 100:.2f}% FC" if s['max_combo'] != s['bmap'].maxCombo() else ''}''')
    e = Embed(description=''.join(des), colour=0x00FFC0)
    e.set_author(
      name=f"best plays for {self[0]['user']['username']}",
      icon_url=self[0]['user']['avatar_url'],
      url=f"https://osu.ppy.sh/users/{self[0]['user']['id']}"
    )
    return e

class Beatmap(Json):
  @property
  def as_embed(self):
    des = 'xd am beatmap'
    e = Embed(description=des, colour=0x00FFC0)
    return e

class Mapset(Json):
  def __init__(self, d):
    self.s = [Beatmap(x) for x in d]

  @property
  def as_embed(self):
    des = []