# AI-Tiku

AI题库答题服务系统。

## Architecture

### Overview

1. Database: SQLite/MySQL, FAISS
2. Model Provider: Ollama, OpenAI-Compatible
3. Agent Framework: LangChain, LangGraph
4. Functions: Key function of the system
5. Web API: FastAPI
6. Web UI: HTML5, MDUI

### Database

#### SQL:

SQLite Path: `data/db.sqlite3`

```sql
-- 用户凭证表
CREATE TABLE `api_tokens` (
  `id` INT UNSIGNED NOT NULL AUTO_INCREMENT COMMENT '主键ID',
  `token` VARCHAR(64) NOT NULL COMMENT '用户唯一凭证',
  `total_queries` INT UNSIGNED NOT NULL DEFAULT 0 COMMENT '总查询次数（题库使用次数）',
  `success_queries` INT UNSIGNED NOT NULL DEFAULT 0 COMMENT '成功查询次数',
  `remaining_queries` INT UNSIGNED NOT NULL DEFAULT 0 COMMENT '剩余查询次数',
  `created_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  `updated_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
  PRIMARY KEY (`id`),
  UNIQUE INDEX `idx_token` (`token`)
) COMMENT='用户凭证及配额表';

-- 题库主表（题目-答案）
CREATE TABLE `questions` (
  `id` INT UNSIGNED NOT NULL AUTO_INCREMENT COMMENT '题目ID',
  `question_text` TEXT NOT NULL COMMENT '题目内容',
  `answer_text` TEXT NOT NULL COMMENT '答案内容',
  `is_ai_generated` TINYINT(1) NOT NULL DEFAULT 0 COMMENT '是否AI生成（0：人工录入，1：AI生成）',
  `source` VARCHAR(100) DEFAULT NULL COMMENT '题目来源（如：教材、题库等）',
  `created_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  `updated_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
  PRIMARY KEY (`id`),
  FULLTEXT INDEX `idx_question_fulltext` (`question_text`) COMMENT '全文索引，用于快速搜索题目'
) COMMENT='题目答案主表';

-- 查询日志表（用于统计和审计）
CREATE TABLE `query_logs` (
  `id` BIGINT UNSIGNED NOT NULL AUTO_INCREMENT COMMENT '日志ID',
  `token_id` INT UNSIGNED NOT NULL COMMENT '关联的token ID',
  `query_text` TEXT NOT NULL COMMENT '用户查询的原始题目',
  `found` TINYINT(1) NOT NULL DEFAULT 0 COMMENT '是否找到答案（0：未找到，1：找到）',
  `created_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '查询时间',
  PRIMARY KEY (`id`),
  INDEX `idx_token_id` (`token_id`),
  INDEX `idx_created_at` (`created_at`),
  CONSTRAINT `fk_query_logs_token` FOREIGN KEY (`token_id`) REFERENCES `api_tokens` (`id`) ON DELETE CASCADE ON UPDATE CASCADE
) COMMENT='查询日志表';

CREATE TABLE `categories` (
  `id` INT UNSIGNED NOT NULL AUTO_INCREMENT,
  `name` VARCHAR(50) NOT NULL,
  `description` TEXT,
  PRIMARY KEY (`id`)
);

CREATE TABLE `question_category` (
  `question_id` INT UNSIGNED NOT NULL,
  `category_id` INT UNSIGNED NOT NULL,
  PRIMARY KEY (`question_id`, `category_id`),
  FOREIGN KEY (`question_id`) REFERENCES `questions` (`id`) ON DELETE CASCADE,
  FOREIGN KEY (`category_id`) REFERENCES `categories` (`id`) ON DELETE CASCADE
);
```

#### Vector Database: FAISS

Vector Path: `data/embeddings/faiss_{category_id}.index`

### Model Provider

Interface:

- embeddings
    - embedding
    - retrieval
- completion/chat
    - streaming
    - async
    - normal

### Agent Framework

- LangChain
- LangGraph

### Functions

- Answer retriever: Search for answers normally based on the question content.
- Answer reviewer: Review and correct history answers by given corrections.
- Classification: Classify questions into different categories.
- RAG based chat: Chat with the question and answer.

## API Document

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
                "200":
                    description: 成功返回查询结果
                    content:
                        application/json:
                            schema:
                                $ref: "#/components/schemas/QueryResponse"
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
                "200":
                    description: 成功返回信息
                    content:
                        application/json:
                            schema:
                                $ref: "#/components/schemas/InfoResponse"
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
                        - $ref: "#/components/schemas/SingleResultData"
                        - $ref: "#/components/schemas/MultiResultData"
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
