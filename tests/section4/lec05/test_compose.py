"""S4 lec05 공통 관심사 합성 테스트.

호출 주입(DI)으로 두 하네스가 한 예산을 공유하는 것을 결정적으로 본다.
"""

import asyncio

import pytest

from section4.lec05.compose import (
    SummarizeHarness,
    TranslateHarness,
    budgeted,
    fake_llm,
)
from section4.lec05.reliability import Budget, BudgetError


def test_budgeted_charges_on_call():
    budget = Budget(100)
    llm = budgeted(fake_llm, budget)
    asyncio.run(llm([{"role": "user", "content": "hello"}]))
    assert budget.spent == len("hello")


def test_two_harnesses_share_one_budget():
    budget = Budget(100)
    llm = budgeted(fake_llm, budget)
    summarize = SummarizeHarness(llm)
    translate = TranslateHarness(llm)
    asyncio.run(summarize.run("aaaa"))
    after_first = budget.spent
    asyncio.run(translate.run("bbbb"))
    assert budget.spent > after_first  # 같은 예산이 둘에 걸쳐 줄어든다


def test_shared_budget_refuses_when_exhausted():
    budget = Budget(5)
    summarize = SummarizeHarness(budgeted(fake_llm, budget))
    with pytest.raises(BudgetError):
        asyncio.run(summarize.run("이건 5토큰보다 길다"))
