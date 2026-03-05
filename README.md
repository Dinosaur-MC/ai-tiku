# AI-Tiku

AI题库答题服务。

## API 文档

```yaml
openapi: 3.0.3
info:
  title: 题库 API
  description: |
    题库开发者接口文档，提供查题及题库信息查询功能。
    
    **注意**：调用前请先在[题库个人中心](https://tk.enncy.cn)获取`token`。
  version: 1.0.0
  contact:
    name: 题库支持
    url: https://tk.enncy.cn
servers:
  - url: https://tk.enncy.cn
    description: 生产服务器

paths:
  /query:
    get:
      summary: 查题接口
      description: |
        根据题目内容搜索答案。支持单题查询和多结果查询（通过`more`参数控制）。
        
        **参数说明**：
        - `title`、`q`、`question` 三个字段至少提供一个，最终接口只会采用其中一个（优先级：`title` > `q` > `question`）。
        - `more` 参数已禁用，保留仅用于兼容旧版本，不建议使用。
      parameters:
        - name: token
          in: query
          description: 用户凭证，请在题库个人中心获取。
          required: true
          schema:
            type: string
        - name: title
          in: query
          description: 查询的题目（与 `q`、`question` 三选一）。
          required: false
          schema:
            type: string
        - name: q
          in: query
          description: 查询的题目（与 `title`、`question` 三选一）。
          required: false
          schema:
            type: string
        - name: question
          in: query
          description: 查询的题目（与 `title`、`q` 三选一）。
          required: false
          schema:
            type: string
        - name: options
          in: query
          description: 选项内容，多个选项用换行符分隔，用于AI辅助答题。
          required: false
          schema:
            type: string
        - name: type
          in: query
          description: 题目类型，用于AI辅助答题。
          required: false
          schema:
            type: string
            enum: [single, multiple, judgement, completion, unknown]
        - name: more
          in: query
          description: 是否返回多个搜索结果（此参数已禁用，不建议使用）。
          required: false
          schema:
            type: boolean
          deprecated: true
      responses:
        '200':
          description: 成功返回查询结果
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/QueryResponse'
              examples:
                singleSuccess:
                  summary: 单条结果（more=false）
                  value:
                    code: 1
                    data:
                      question: "中国梦是什么？"
                      answer: "实现中华民族伟大复兴，本质是国家富强、民族振兴、人民幸福。"
                      times: 666
                    message: "请求成功"
                singleNotFound:
                  summary: 未找到答案（单条模式）
                  value:
                    code: 0
                    data:
                      question: "未找到答案！"
                      answer: "很抱歉, 题目搜索不到。"
                      times: 665
                    message: "请求失败"
                multiSuccess:
                  summary: 多条结果（more=true）
                  value:
                    code: 1
                    data:
                      results:
                        - question: "中国梦是什么？"
                          answer: "实现中华民族伟大复兴，本质是国家富强、民族振兴、人民幸福。"
                      times: 666
                    message: "请求成功"
                multiNotFound:
                  summary: 未找到答案（多条模式）
                  value:
                    code: 0
                    data:
                      results: []
                      times: 665
                    message: "请求失败"

  /info:
    get:
      summary: 题库信息获取接口
      description: 获取当前 token 的剩余调用次数、总使用次数及成功次数。
      parameters:
        - name: token
          in: query
          description: 用户凭证，请在题库个人中心获取。
          required: true
          schema:
            type: string
      responses:
        '200':
          description: 成功返回信息
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/InfoResponse'
              example:
                code: 1
                data:
                  times: 1000
                  user_times: 5000
                  success_times: 4800
                message: "请求成功"

components:
  schemas:
    QueryResponse:
      type: object
      properties:
        code:
          type: integer
          description: 1 表示有答案，0 表示无答案
          enum: [0, 1]
        message:
          type: string
          description: 请求结果描述
        data:
          oneOf:
            - $ref: '#/components/schemas/SingleResultData'
            - $ref: '#/components/schemas/MultiResultData'
      required:
        - code
        - message
        - data

    SingleResultData:
      type: object
      properties:
        question:
          type: string
          description: 搜索到的题目（可能与查询的 title 不完全一致）
        answer:
          type: string
          description: 答案内容
        times:
          type: integer
          description: 接口剩余次数
        ai:
          type: boolean
          description: 若为 true 表示答案为 AI 生成（可能不存在）
      required:
        - question
        - answer
        - times

    MultiResultData:
      type: object
      properties:
        results:
          type: array
          description: 搜索结果列表
          items:
            type: object
            properties:
              question:
                type: string
              answer:
                type: string
              ai:
                type: boolean
                description: 若为 true 表示答案为 AI 生成（可能不存在）
            required:
              - question
              - answer
        times:
          type: integer
          description: 接口剩余次数
      required:
        - results
        - times

    InfoResponse:
      type: object
      properties:
        code:
          type: integer
          description: 1 表示成功，0 表示失败
          enum: [0, 1]
        message:
          type: string
          description: 请求结果描述
        data:
          type: object
          properties:
            times:
              type: integer
              description: 接口剩余次数
            user_times:
              type: integer
              description: 题库使用总次数
            success_times:
              type: integer
              description: 题库搜索成功次数
          required:
            - times
            - user_times
            - success_times
      required:
        - code
        - message
        - data
```

