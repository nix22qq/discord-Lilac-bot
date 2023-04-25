import os
import discord
import asyncio
from discord.ext import commands
import re
from datetime import timedelta

intents = discord.Intents.default()
intents.typing = False
intents.presences = False
intents.messages = True

bot = commands.Bot(command_prefix="!", intents=intents)

user_request_status = {}
user_request_number = {}
exchange_requests = {}



def parse_time(time_str):
    match = re.match(r"(\d+)시간 (\d+)분", time_str)
    if match:
        hours, minutes = map(int, match.groups())
        return timedelta(hours=hours, minutes=minutes)
    return None


def save_time(user_id, time):
    file_path = f"times/{user_id}.txt"
    total_time = timedelta()

    if os.path.exists(file_path):
        with open(file_path, "r") as f:
            total_time = timedelta(minutes=int(f.read()))

    total_time += time

    with open(file_path, "w") as f:
        f.write(str(int(total_time.total_seconds() // 60)))


def save_class(user_id, class_name):
    file_path = f"myclass/{class_name}.txt"

    with open(file_path, "a") as f:
        f.write(f"{user_id}\n")


def calculate_total_time(class_name):
    file_path = f"myclass/{class_name}.txt"
    total_time = timedelta()

    if os.path.exists(file_path):
        with open(file_path, "r") as f:
            for line in f:
                user_id = int(line.strip())
                time_file_path = f"times/{user_id}.txt"

                if os.path.exists(time_file_path):
                    with open(time_file_path, "r") as time_file:
                        user_time = timedelta(minutes=int(time_file.read()))
                        total_time += user_time

    return total_time



@bot.event
async def on_ready():
    
    print(f"{bot.user.name} is online!")
    for file_name in os.listdir("txts"):
        if file_name.startswith("messages_"):
            user_id, message_id = map(int, file_name[9:-4].split("_"))
            user_request_number[user_id] = max(user_request_number.get(user_id, 0), message_id)
    


@bot.event
async def on_message(message):
    if message.author == bot.user:
        return

    msg = message.content.lower()

    if msg == "안녕":
        await message.channel.send("안녕하세요!")

    elif msg == "업로드":
        user_request_status[message.author.id] = True
        user_request_number[message.author.id] = user_request_number.get(message.author.id, 0) + 1
        await message.channel.send("이미지와 글을 업로드 해주세요!")

    elif message.author.id in user_request_status and user_request_status[message.author.id]:
        user_number = user_request_number[message.author.id]
        received = False

        if message.attachments:
            for attachment in message.attachments:
                file_path = f"./downloads/{message.author.id}_{user_number}_image.jpg"
                await attachment.save(file_path)
                print(f"File saved: {file_path}")
                received = True

        with open(f"txts/messages_{message.author.id}_{user_number}.txt", "a", encoding="utf-8") as f:
            f.write(f"{message.content}\n")
            received = True

        if received:
            await message.channel.send("받았습니다!")
        user_request_status[message.author.id] = False
        
    elif msg.startswith("삭제"):
        _, message_id = msg.split()
        message_id = int(message_id)
        text_file_path = f"txts/messages_{message.author.id}_{message_id}.txt"

        removed_text = False
        removed_image = False

        if os.path.exists(text_file_path):
            os.remove(text_file_path)
            removed_text = True

        user_id = message.author.id
        for file_name in os.listdir("./downloads"):
            if file_name.startswith(f"{user_id}_{message_id}_"):
                file_path = f"./downloads/{file_name}"
                os.remove(file_path)
                print(f"File removed: {file_path}")
                removed_image = True

        if removed_text and removed_image:
            await message.channel.send(f"{message_id}번 글과 이미지를 삭제했습니다.")
        elif removed_text:
            await message.channel.send(f"{message_id}번 글을 삭제했습니다.")
        elif removed_image:
            await message.channel.send(f"{message_id}번 이미지를 삭제했습니다.")
        else:
            await message.channel.send("해당 글과 이미지를 찾을 수 없습니다.")
            
    elif msg == "전체 글":
        all_messages = []
        for user_id in user_request_number:
            user = await bot.fetch_user(user_id)
            user_messages = []
            for i in range(1, user_request_number[user_id] + 1):
                file_path = f"txts/messages_{user_id}_{i}.txt"
                if os.path.exists(file_path):
                    with open(file_path, "r", encoding="utf-8") as f:
                        content = f.read().strip()
                    user_messages.append(f"{user.name}, {user_id}:{i}. {content}")
            if user_messages:
                all_messages.extend(user_messages)
        if all_messages:
            await message.channel.send("\n".join(all_messages))
            await message.channel.send("어떤 글을 선택하시겠습니까? ([사용자 번호:글 번호] 형식으로 입력해주세요.)")
            try:
                msg = await bot.wait_for("message", timeout=30.0, check=lambda m: m.author == message.author)
                msg_parts = msg.content.split(":")
                if len(msg_parts) != 2:
                    raise ValueError
                user_id, message_id = msg_parts
                user_id = int(user_id)
                message_id = int(message_id)
                file_path = f"./downloads/{user_id}_{message_id}_image.jpg"
                if os.path.exists(file_path):
                    with open(file_path, 'rb') as fp:
                        img = discord.File(fp)
                        await message.channel.send(file=img)
                else:
                    await message.channel.send("해당 글의 이미지를 찾을 수 없습니다.")
            except asyncio.TimeoutError:
                await message.channel.send("시간이 초과되었습니다. 다시 시도해주세요.")
            except (ValueError, KeyError):
                await message.channel.send("잘못된 입력입니다. 다시 시도해주세요.")
        else:
            await message.channel.send("저장된 글이 없습니다.")

    
    elif msg == "내 글":
        user_id = message.author.id
        user_messages = []

        for i in range(1, user_request_number.get(user_id, 0) + 1):
            file_path = f"txts/messages_{user_id}_{i}.txt"

            if os.path.exists(file_path):
                with open(file_path, "r", encoding="utf-8") as f:
                    content = f.read().strip()
                user_messages.append(f"{i}. {content}")

        if user_messages:
            await message.channel.send(f"{message.author.name}님의 글 목록:\n" + "\n".join(user_messages))
            await message.channel.send("어떤 글을 보시겠습니까? (숫자를 입력하세요.)")
            try:
                msg = await bot.wait_for("message", timeout=30.0, check=lambda m: m.author == message.author and m.content.isdigit())
                msg_num = int(msg.content)
                file_path = f"./downloads/{user_id}_{msg_num}_image.jpg"
                if os.path.exists(file_path):
                    with open(file_path, 'rb') as fp:
                        img = discord.File(fp)
                        await message.channel.send(file=img)
                else:
                    await message.channel.send("해당 글의 이미지를 찾을 수 없습니다.")
            except asyncio.TimeoutError:
                await message.channel.send("시간이 초과되었습니다. 다시 시도해주세요.")
            except ValueError:
                await message.channel.send("잘못된 입력입니다. 다시 시도해주세요.")
        else:
            await message.channel.send("저장된 글이 없습니다.")
            
            
    elif msg.startswith("시간 "):
            time_str = msg[3:]
            time = parse_time(time_str)

            if time is not None:
                save_time(message.author.id, time)
                await message.channel.send(f"{time_str} 저장되었습니다.")
            else:
                await message.channel.send("올바른 시간 형식을 입력하세요. 예) 시간 6시간 12분")

    elif msg.startswith("등록 "):
        class_name = msg[3:]

        if class_name in ["1-1", "1-2", "1-3", "1-4", "1-5", "1-6", "1-7", "1-8", "2-1", "2-2", "2-3", "2-4", "2-5", "2-6", "2-7", "2-8", "3-1", "3-2", "3-3", "3-4", "3-5", "3-6", "3-7", "3-8"]:
            save_class(message.author.id, class_name)
            await message.channel.send(f"{class_name} 반에 등록되었습니다.")
        else:
            await message.channel.send("올바른 반을 입력하세요. 예) 등록 1-2")

    elif msg.startswith("합계 "):
        class_name = msg[3:]
        if class_name in ["1-1", "1-2", "1-3", "1-4", "1-5", "1-6", "1-7", "1-8", "2-1", "2-2", "2-3", "2-4", "2-5", "2-6", "2-7", "2-8", "3-1", "3-2", "3-3", "3-4", "3-5", "3-6", "3-7", "3-8"]:
            total_time = calculate_total_time(class_name)
            hours, remainder = divmod(total_time.seconds, 3600)
            minutes = remainder // 60
            await message.channel.send(f"{class_name} 반의 총 시간: {hours}시간 {minutes}분")
        else:
            await message.channel.send("올바른 반을 입력하세요. 예) 합계 1-2")


    elif msg == "내 시간":
        user_id = message.author.id
        file_path = f"times/{user_id}.txt"
        if os.path.exists(file_path):
            with open(file_path, "r") as f:
                total_minutes = int(f.read())
                hours, remainder = divmod(total_minutes, 60)
                minutes = remainder
            await message.channel.send(f"{message.author.name}님의 저장된 시간: {hours}시간 {minutes}분")
        else:
            await message.channel.send("저장된 시간이 없습니다.")
            
    elif msg == "도움":
        help_message = """
이 봇은 다음 기능을 지원합니다:
1. "안녕" - 봇이 인사합니다.
2. "업로드" - 글과 이미지를 업로드 할 수 있습니다.
3. "삭제 [글 번호]" - 지정된 번호의 글과 이미지를 삭제합니다.
4. "전체 글" - 모든 사용자의 글 목록을 보여줍니다.
5. "내 글" - 자신의 글 목록을 보여줍니다.
6. "시간 [시간]시간 [분]분" - 자신의 시간을 저장합니다. 예) 시간 6시간 12분
7. "등록 [반 이름]" - 지정된 반에 등록합니다. 예) 등록 1-2
8. "합계 [반 이름]" - 지정된 반의 총 시간을 보여줍니다. 예) 합계 1-2
9. "내 시간" - 저장된 시간을 보여줍니다.
10. "도움" - 이 도움말을 보여줍니다.
11. "학생 랭킹" - 학생들의 시간을 랭킹순으로 보여줍니다.
"""

        await message.channel.send(help_message)



    elif msg == "학생 랭킹":
        student_times = []
        for file_name in os.listdir("times"):
            user_id = int(file_name[:-4])
            user = await bot.fetch_user(user_id)

            with open(f"times/{file_name}", "r") as f:
                total_minutes = int(f.read())
            student_times.append((user.name, total_minutes))
        student_times.sort(key=lambda x: x[1], reverse=True)
        rank_message = ""
        for i, (name, total_minutes) in enumerate(student_times[:4]):
            hours, remainder = divmod(total_minutes, 60)
            minutes = remainder
            if i == 0:
                rank_message += f"1등: {name} {hours}시간 {minutes}분\n"
            elif i == 1:
                rank_message += f"2등: {name} {hours}시간 {minutes}분\n"
            elif i == 2:
                rank_message += f"3등: {name} {hours}시간 {minutes}분\n"
            else:
                rank_message += f"{i+1}등: {name} {hours}시간 {minutes}분\n"
        await message.channel.send(rank_message)




bot.run("token")
