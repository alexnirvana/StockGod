"""Canonical teaching explanations shared by the API and narrated audio build."""
ANSWERS = {
    'boundary': '这里的教练只帮助你理解课程和模拟规则。教学数据不能用来预测真实股票。可以问我如何查看资金、理解费用或解释订单状态。',
    'orders': '提交订单后先冻结资金或持仓，订单显示“待处理”。推进下一教学日才按开盘参考价检查限价；不满足价格条件或停牌时不会成交。请打开订单结果查看具体原因。',
    'costs': '教学费用由佣金、过户费和卖出时的印花税构成。佣金按成交金额的 0.03% 估算、每笔至少 5 元，这是教学假设。每笔成交都会列出实际扣除的费用。',
    'positions': '总持仓包含今天刚买入的股票；可卖数量还要扣除当日买入和待处理卖单冻结的数量。本场景当日买入，下一教学日才可卖出。',
    'example': '换个例子：账户现金 30,000 元，待处理买单冻结 5,000 元，可用资金就是 25,000 元。撤销这张待处理买单后，5,000 元会释放，现金总额没有因此增加。',
}


def topic(question):
    question = question.lower()
    for english, keyword in [('predict', '预测'), ('tomorrow', '明天'), ('recommend', '推荐'), ('which stock', '买哪'), ('order', '订单'), ('fill', '订单'), ('fee', '费用'), ('cost', '成本'), ('commission', '佣金'), ('sell', '卖'), ('holding', '持仓'), ('position', '持仓'), ('example', '例')]:
        if english in question:
            question += keyword
    for key, words in [('boundary', ('推荐', '明天', '预测', '涨停', '买哪')), ('orders', ('不成交', '没成交', '委托', '下单', '订单')), ('costs', ('费用', '成本', '佣金')), ('positions', ('卖', '持仓', 't+1')), ('example', ('例',))]:
        if any(word in question for word in words):
            return key
    return None
