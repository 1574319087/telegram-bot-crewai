from crewai import Agent, Task, Crew
from crewai.tools import tool
import feedparser, os, asyncio
from telegram import Bot
from apscheduler.schedulers.background import BackgroundScheduler

@tool("geo_fed_scanner")
def geo_fed_scanner() -> str:
    """每10秒扫描战争、地缘、美联储新闻"""
    feeds = [
        "https://www.federalreserve.gov/rss/fomcminutes.xml",
        "https://feeds.reuters.com/reuters/businessNews",
        "https://rss.nytimes.com/services/xml/rss/nyt/World.xml"
    ]
    events = []
    keywords = ["war", "ukraine", "israel", "taiwan", "powell", "rate hike", "rate cut", "fed", "geopolitics"]
    for url in feeds:
        feed = feedparser.parse(url)
        for entry in feed.entries[:5]:
            text = (entry.title + entry.get("summary", "")).lower()
            if any(kw in text for kw in keywords):
                events.append(f"🚨 {entry.title}\n{entry.link}")
    return "\n".join(events[:3]) if events else "无新敏感事件"

news_agent = Agent(role="新闻哨兵", goal="实时抓敏感事件", tools=[geo_fed_scanner], llm="groq/llama3-70b-8192")
signal_agent = Agent(role="币圈信号分析师", goal="给出 BTC/ETH 买卖概率和建议", llm="groq/llama3-70b-8192")
alert_agent = Agent(role="Telegram报警员", goal="把信号发给你", llm="groq/llama3-70b-8192")

async def run_crew():
    task1 = Task(description="扫描最新敏感事件", agent=news_agent, expected_output="事件列表")
    task2 = Task(description="根据事件分析 BTC/ETH 交易信号（概率+建议）", agent=signal_agent, expected_output="信号")
    
    crew = Crew(agents=[news_agent, signal_agent], tasks=[task1, task2], verbose=1)
    result = crew.kickoff()
    
    bot = Bot(token=os.getenv("TELEGRAM_TOKEN"))
    await bot.send_message(chat_id=os.getenv("TELEGRAM_CHAT_ID"), text=str(result))

# 启动每10秒自动运行
scheduler = BackgroundScheduler()
scheduler.add_job(lambda: asyncio.run(run_crew()), 'interval', seconds=10)
scheduler.start()

# 保持进程不退出
import time
while True:
    time.sleep(60)
