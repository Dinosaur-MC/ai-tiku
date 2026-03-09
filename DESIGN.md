---
name: prototype of AI-Tiku Project
description: AI-Tiku 项目原型设计与开发计划
labels: [prototype]
assignees: [Dinosaur-MC@github.com]
llm-accessibility: readonly
---

> ⚠️ 本文档仅限人工编写与审核，请勿使用 LLM 或 AI 直接修改此文档。
> ⚠️ 本文档仍在扩充与完善中，可能随时被修改。

---

# AI-Tiku 项目设计（一期）

## 项目简介

AI-Tiku 是一个基于 LLM 的题库查询和知识库问答系统，提供智能题库查询和问题解答服务。
项目基于 Python 语言开发，使用 FastAPI 框架构建 API 接口，使用 SQLite 关系数据库和 FAISS 向量数据库进行数据存储。

## 核心功能

- [ ] 智能题库查询
    - [ ] 基于向量相似度搜索
    - [ ] 基于 LLM 的智能问题分类
- [ ] AI 辅助答题
    - [x] 基于 LLM 的实时问题解答
    - [ ] 基于 AI Agent 的智能问题录入
        - [ ] 问题批量审核与查证
        - [ ] 问题批量修正
- [ ] 账户与配额管理
    - [ ] 账户管理
    - [x] 配额管理
    - [ ] RBAC (Role-Based Access Control)
- [ ] 管理员功能和界面
    - [ ] 问题管理
    - [ ] 用户管理
    - [ ] 模型管理
    - [ ] 日志分析
    - [ ] 性能监控

## 核心任务流

问题查询：

```mermaid
graph LR

A[Collect Question]
--> B[Encode Question]
--> C[Query API]
--> D[Decode Answer]
--> E[Query Database]
--> F{has answer?}
-->|N| G[Invoke LLM]
--> H[Return Answer]
--> I[Decode Answer]
--> J[Fill in Answer]

F-->|Y|H
```

问题分类：

```mermaid
graph LR


```

问题审核与修正：

```mermaid
graph LR


```

问题录入：

```mermaid
graph LR


```

## 技术栈

- uv
- Python 3.12
    - FastAPI
    - FAISS
    - Langchain
        - langchain
        - langchain-community
        - langchain-ollama
        - langchain-openai
        - langchain-openrouter
        - langchain-text-splitters
        - langgraph
    - Ollama
    - Pydantic
    - PySqlite3
    - PyTest
    - SQLModel
    - Uvicorn

## 项目架构

## 目录结构

---

# AI-Tiku 项目设计（二期）

...
