from flask import Flask, request
import requests
import json
from mattermostdriver import Driver
from redminelib import Redmine
import openai
import os

app = Flask(__name__)

md = Driver({
    'url': os.environ['MATTERMOST_HOST'],
    'login_id': os.environ['MATTERMOST_LOGIN_ID'],
    'token': os.environ['MATTERMOST_TOKEN'],
    'scheme': os.environ['MATTERMOST_SCHEME'],
    'port': int(os.environ['MATTERMOST_PORT']),
})
redmine = Redmine(os.environ['REDMINE_HOST'], key=os.environ['REDMINE_API_TOKEN'])
openai.api_key = os.environ['OPENAI_API_KEY']

def get_summary(text):
    system = """与えられた会話の要点を、以下の観点でそれぞれ最大50字でまとめ、日本語で出力してください。```
    ・現在の状況
    ・やるべきこと
    ```"""

    response = openai.ChatCompletion.create(
                model="gpt-3.5-turbo",
                messages=[
                    {'role': 'system', 'content': system},
                    {'role': 'user', 'content': text}
                ],
                temperature=0.25,
            )
    summary = response['choices'][0]['message']['content']
    
    return summary

def get_summary_title(text):
    system = """与えられた文章の要点を最大20字でまとめ、日本語で出力してください。"""

    response = openai.ChatCompletion.create(
                model="gpt-3.5-turbo",
                messages=[
                    {'role': 'system', 'content': system},
                    {'role': 'user', 'content': text}
                ],
                temperature=0.25,
            )
    summary_title = response['choices'][0]['message']['content']
    
    return summary_title

@app.route('/matter', methods=['POST'])
def post():
    data = request.json
    post_id = data['text'].split('/')[-1]
    md.login()
    text = ''
    message = ''
    try:
      root_id = md.posts.get_post(post_id)['root_id']
      if root_id != '':
        post_id = root_id
      thread = md.posts.get_thread(post_id)
      for k in thread['order']:
        text += thread['posts'][k]['message'] + '\n'
      summary_text = get_summary(text)
      summary_title = get_summary_title(summary_text)
      issue = redmine.issue.new()
      issue.project_id = os.environ['REDMINE_PROJECT_ID']
      issue.subject = summary_title
      issue.description = summary_text
      res = issue.save()
      message = "チケットを作成しました。\n" + res.url
    except:
       message = '対象ポストのURLを指定してください'
    md.posts.create_post(options={
        'channel_id': os.environ['MATTERMOST_CHANNEL_ID'],  
        'message': message
    })    
    md.logout()    
    return json.dumps(dict())

if __name__ == "__main__":
  app.run(host="0.0.0.0", port=80, debug=True)