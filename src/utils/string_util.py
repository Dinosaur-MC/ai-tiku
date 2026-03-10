def common_prefix(str1: str, str2: str) -> str:
    """
    返回两个字符串的公共前缀。
    如果没有公共前缀，返回空字符串。
    """

    # 输入类型检查
    if not isinstance(str1, str) or not isinstance(str2, str):
        raise TypeError("Both inputs must be strings.")

    # 如果有任意一个为空，直接返回空字符串
    if not str1 or not str2:
        return ""

    # 遍历比较字符
    prefix_chars = []
    for ch1, ch2 in zip(str1, str2):
        if ch1 == ch2:
            prefix_chars.append(ch1)
        else:
            break  # 一旦不同就停止

    return "".join(prefix_chars)
