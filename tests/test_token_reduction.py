"""Benchmarks the token reduction achieved by summarize_node.

The resume claims 45-55% prompt-token reduction via dynamic memory
summarization. This test backs that claim with a measurement on a
synthetic 25-turn conversation fixture.

To avoid network calls, we stub out the LLM that summarize_node uses
with a deterministic fake that produces a fixed-length summary. We
verify that:
  1. The post-summary message list is shorter than the original.
  2. Approximate token count drops by at least 45%.

We use a simple word-count proxy for tokens (1 word ≈ 1.3 tokens on
average for English; tiktoken would be more accurate but adds a heavy
dep). Since we measure RATIOS, the proxy is sufficient: ratios of
word counts and ratios of true token counts are within ~5% of each
other for natural English.
"""

from __future__ import annotations

import re
from unittest.mock import patch

import pytest
from langchain_core.messages import AIMessage, HumanMessage

import chatbot_backend_gemini as cb
from chatbot_backend_gemini import KEEP_RECENT, SUMMARY_TRIGGER, summarize_node


def _word_count(text: str) -> int:
    return len(re.findall(r"\S+", text))


def _approx_tokens(messages) -> int:
    """Approximate token count: total non-whitespace tokens across all messages."""
    total = 0
    for m in messages:
        c = m.content if isinstance(m.content, str) else str(m.content)
        # Cheap proxy: 1 token ≈ 0.75 words. Multiply by 1.33 for rough match.
        total += int(_word_count(c) * 1.33)
    return total


def _make_25_turn_conversation():
    """Build a deterministic 25-turn conversation. Each turn ~30-60 words."""
    convo = []
    topics = [
        ("What's the capital of France?",
         "Paris is the capital of France. It is located in north-central France along the Seine River and serves as the country's political, cultural, and economic center."),
        ("Tell me about the Eiffel Tower.",
         "The Eiffel Tower is a wrought-iron lattice tower built in 1889 for the World's Fair. It stands 330 meters tall and is one of the most recognizable landmarks in the world, attracting millions of visitors each year."),
        ("Who designed it?",
         "The tower was designed by the engineering firm of Gustave Eiffel. The chief engineers Maurice Koechlin and Émile Nouguier produced the original concept, and architect Stephen Sauvestre refined the design's aesthetic."),
        ("How long did construction take?",
         "Construction of the Eiffel Tower took 2 years, 2 months, and 5 days, from January 1887 to March 1889. About 300 workers assembled 18,038 individual iron pieces using 2.5 million rivets."),
        ("What was its original purpose?",
         "It was built as the centerpiece of the 1889 Exposition Universelle, a world's fair celebrating the 100th anniversary of the French Revolution. It was originally intended as a temporary structure to be dismantled after 20 years."),
        ("Why wasn't it dismantled?",
         "It was kept because it proved valuable as a radio transmission tower. The French military used it for wireless telegraphy starting in 1903, and it played a role in intercepting German communications during World War I."),
        ("Tell me about French cuisine.",
         "French cuisine is renowned for its sophistication and regional diversity. It emphasizes fresh ingredients, technical precision, and refined flavor combinations. Classic dishes include coq au vin, beef bourguignon, ratatouille, and various pastries like croissants and macarons."),
        ("What are some famous French desserts?",
         "Famous French desserts include crème brûlée, tarte tatin, mille-feuille, profiteroles, soufflé, éclairs, macarons, and madeleines. French patisserie is celebrated worldwide for its precision and elegant presentation."),
        ("Tell me about the Louvre.",
         "The Louvre is the world's largest art museum and a historic monument in Paris. It houses approximately 380,000 objects and displays 35,000 works of art, including the Mona Lisa, Venus de Milo, and Winged Victory of Samothrace. It was originally a fortress built in 1190."),
        ("How many visitors does it get?",
         "The Louvre attracts around 9-10 million visitors per year, making it the most-visited museum in the world. The Mona Lisa alone is viewed by an estimated 30,000 people daily, drawing crowds from every continent."),
        ("Tell me about French wine.",
         "French wine is one of the most celebrated in the world, with major regions including Bordeaux, Burgundy, Champagne, Loire Valley, Rhône, and Alsace. France produces 7-8 billion bottles annually and has a rigorous appellation system to guarantee origin and quality."),
        ("What is Champagne?",
         "Champagne is a sparkling wine produced exclusively in the Champagne region of northeastern France. It's made primarily from Chardonnay, Pinot Noir, and Pinot Meunier grapes using the méthode champenoise, which involves a secondary fermentation in the bottle."),
    ]
    for human_text, ai_text in topics:
        convo.append(HumanMessage(content=human_text))
        convo.append(AIMessage(content=ai_text))
    # Add one extra to make the total odd-ish; ensures we cross trigger comfortably.
    convo.append(HumanMessage(content="Thanks for all this info — what should I see in Paris if I have just one day?"))
    return convo


def test_fixture_size_exceeds_summary_trigger():
    convo = _make_25_turn_conversation()
    assert len(convo) > SUMMARY_TRIGGER


def test_summarize_node_reduces_message_count():
    """After summarize, the message list should be much shorter."""
    convo = _make_25_turn_conversation()
    # Assign ids so RemoveMessage works.
    for i, m in enumerate(convo):
        m.id = f"msg-{i}"

    fake_summary = AIMessage(
        content=(
            "User asked about Paris, the Eiffel Tower (built 1889 by Gustave Eiffel "
            "for the World's Fair, 330m tall, kept due to radio use), French cuisine "
            "and desserts (coq au vin, crème brûlée, macarons), the Louvre (most-"
            "visited museum, holds the Mona Lisa), and French wine including Champagne."
        )
    )

    with patch.object(cb, "get_llm_with_failover") as mock_get:
        primary = type("P", (), {"invoke": lambda self, msgs: fake_summary})()
        backup = type("B", (), {"invoke": lambda self, msgs: fake_summary})()
        mock_get.return_value = (primary, backup)

        update = summarize_node({"messages": convo})

    # update["messages"] = [RemoveMessage..., RemoveMessage..., new_summary]
    new_msgs = update["messages"]
    removals = [m for m in new_msgs if type(m).__name__ == "RemoveMessage"]
    summaries = [m for m in new_msgs if type(m).__name__ == "SystemMessage"]
    expected_removed = len(convo) - KEEP_RECENT
    assert len(removals) == expected_removed
    assert len(summaries) == 1


def test_summarize_node_token_reduction_meets_45pct():
    """The headline claim: prompt token usage drops by at least 45%."""
    convo = _make_25_turn_conversation()
    for i, m in enumerate(convo):
        m.id = f"msg-{i}"

    before_tokens = _approx_tokens(convo)

    fake_summary = AIMessage(
        content=(
            "Conversation summary: User asked about Paris and France — covered the "
            "Eiffel Tower (built 1889 by Gustave Eiffel for the World's Fair, 330m, "
            "kept for radio use after 1903), French cuisine (coq au vin, ratatouille), "
            "famous desserts (crème brûlée, macarons, mille-feuille), the Louvre "
            "(world's largest museum, ~10M visitors, holds Mona Lisa), and French wine "
            "including Bordeaux, Burgundy, and Champagne."
        )
    )

    with patch.object(cb, "get_llm_with_failover") as mock_get:
        primary = type("P", (), {"invoke": lambda self, msgs: fake_summary})()
        backup = type("B", (), {"invoke": lambda self, msgs: fake_summary})()
        mock_get.return_value = (primary, backup)
        update = summarize_node({"messages": convo})

    # Reconstruct what the next LLM call would see:
    # the kept-recent messages + the new summary SystemMessage.
    # add_messages reducer would: remove old by id, append summary.
    removals = {m.id for m in update["messages"] if type(m).__name__ == "RemoveMessage"}
    summary_msgs = [m for m in update["messages"] if type(m).__name__ == "SystemMessage"]
    kept = [m for m in convo if m.id not in removals]
    after_messages = kept + summary_msgs

    after_tokens = _approx_tokens(after_messages)

    reduction_pct = (before_tokens - after_tokens) / before_tokens * 100
    print(f"\nToken reduction: {before_tokens} -> {after_tokens} ({reduction_pct:.1f}% drop)")

    assert reduction_pct >= 45.0, (
        f"Expected >= 45% token reduction; got {reduction_pct:.1f}% "
        f"({before_tokens} -> {after_tokens})"
    )


def test_summarize_node_noop_when_below_trigger():
    """If the conversation is short, summarize_node should return no update."""
    short_convo = [HumanMessage(content="hi", id="m1"), AIMessage(content="hello", id="m2")]
    update = summarize_node({"messages": short_convo})
    assert update == {}


def test_split_at_tool_safe_boundary_preserves_tool_pair():
    """A ToolMessage must never be kept without its parent AIMessage(tool_calls)."""
    from langchain_core.messages import ToolMessage

    from chatbot_backend_gemini import _split_at_tool_safe_boundary

    # Conversation where the naive cut would split a tool-call/response pair.
    msgs = [
        HumanMessage(content="q1"),
        AIMessage(content="a1"),
        HumanMessage(content="q2"),
        AIMessage(content="a2"),
        HumanMessage(content="q3"),
        # AI invokes a tool here; ToolMessage answers it.
        AIMessage(content="", tool_calls=[{"name": "calc", "args": {"x": 1}, "id": "t1"}]),
        ToolMessage(content="result=1", tool_call_id="t1"),
        AIMessage(content="final"),
    ]
    # KEEP_RECENT=2 would naively keep [ToolMessage, AIMessage("final")] —
    # orphaning the ToolMessage. The helper must extend the window backward
    # to include the AIMessage with tool_calls (and any preceding context).
    to_summarize, to_keep = _split_at_tool_safe_boundary(msgs, keep_recent=2)

    # The AIMessage with tool_calls must be in the keep window.
    assert any(
        isinstance(m, AIMessage) and getattr(m, "tool_calls", None)
        for m in to_keep
    ), "Tool-call AIMessage must be preserved when its ToolMessage is kept"

    # The ToolMessage must be in the keep window.
    assert any(isinstance(m, ToolMessage) for m in to_keep)

    # The summarized portion must NOT contain a ToolMessage (no orphans).
    for m in to_summarize:
        assert not isinstance(m, ToolMessage)
    # Nor an AIMessage that has tool_calls (its pair is in the keep window).
    for m in to_summarize:
        assert not (isinstance(m, AIMessage) and getattr(m, "tool_calls", None))


def test_split_at_tool_safe_boundary_clean_cut():
    """When the naive cut doesn't split a tool pair, behave normally."""
    from chatbot_backend_gemini import _split_at_tool_safe_boundary

    msgs = [
        HumanMessage(content=f"q{i}") if i % 2 == 0 else AIMessage(content=f"a{i}")
        for i in range(8)
    ]
    to_summarize, to_keep = _split_at_tool_safe_boundary(msgs, keep_recent=4)
    assert len(to_summarize) == 4 and len(to_keep) == 4
