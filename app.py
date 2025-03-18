import re
import time

import pandas as pd
import chainlit as cl
import openai
from ultis import *
from langchain.sql_database import SQLDatabase
from langchain_community.tools.sql_database.tool import QuerySQLDatabaseTool

db = SQLDatabase.from_uri(SUPABASE_URI)
execute_query_tool = QuerySQLDatabaseTool(db=db)
@cl.on_message
async def chat_with_gpt(message: cl.Message):
    start_time = time.time()
    # Kiểm tra nếu đã có lịch sử chat trước đó, nếu không thì tạo mới
    if not cl.user_session.get("conversation_history"):
        cl.user_session.set("conversation_history", SYSTEM_CONTEXT.copy())
    print(SYSTEM_CONTEXT)
    # Lấy lịch sử hội thoại hiện tại
    conversation_history = cl.user_session.get("conversation_history")

    # Thêm tin nhắn người dùng vào hội thoại
    conversation_history.append({"role": "user", "content": message.content})

    # Gọi API OpenAI để lấy phản hồi
    response = openai.chat.completions.create(
        model="gpt-4o",
        messages=conversation_history
    )

    # Lấy nội dung phản hồi
    assistant_reply = response.choices[0].message.content

    # Thêm phản hồi vào lịch sử hội thoại
    conversation_history.append({"role": "assistant", "content": assistant_reply})

    # Lưu lại hội thoại vào session để duy trì context
    cl.user_session.set("conversation_history", conversation_history)
    sql_code = extract_sql_query(assistant_reply)
    if sql_code:
        try:
            print("Running SQL Query:", sql_code)
            result = execute_query_tool.run(sql_code)
            conversation_history.append({"role": "user", "content": f" câu hỏi trên cho ra lệnh sql query là {sql_code} kết quả là: {result}, dựa vào dữ liệu trên, hãy biểu diễn dữ liệu trên bảng và hiển thị SQL query cũng như giải thích câu truy vấn dựa trên câu hỏi trên, nếu kết quả của câu truy vấn là không có dữ liệu, thì không cần giải thích"})
            final_res = openai.chat.completions.create(
            model="gpt-4o",
            messages=conversation_history
            )
            final_ans = final_res.choices[0].message.content
            final_ans = final_ans+"\n \nThời gian phản hồi: "+str(time.time()-start_time)
            await cl.Message(content=final_ans).send()
        except Exception as e:
            await cl.Message({e}).send()
    else:
        await cl.Message(assistant_reply).send()



# Hàm nhận diện đoạn code SQL từ assistant_reply
def extract_sql_query(text):
    sql_pattern = r"```sql\n(.*?)\n```"
    match = re.search(sql_pattern, text, re.DOTALL)
    return match.group(1) if match else None
    # Gửi phản hồi về UI Chainlit
    
