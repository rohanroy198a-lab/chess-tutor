from typing import List, Optional

import chess

SYSTEM_PROMPT = """You are a precise chess coach. Explain the player's latest move in concise, natural English.

Rules:
- Use English only.
- Be direct and informative. Usually 1-2 short sentences; no filler, generic praise, clichés, or lists.
- Explain the concrete strategic idea, tactical consequence, or positional weakness supported by the supplied engine data.
- Never invent a threat, tactic, variation, opening name, or engine conclusion.
- The engine's best move and evaluation are authoritative. If the data does not establish why a move works, state only what can be supported.
- For best/excellent moves, explain the useful idea instead of praising the player.
- For inaccuracies, mistakes, and blunders, state what changed and name the engine's preferred move when supplied.
- Do not claim a move wins material or leads to mate unless the supplied data supports that claim.
- If the game ended, state the result briefly.
"""


def _format_eval(cp: Optional[int], mate: Optional[int]) -> str:
    if mate is not None:
        if mate > 0:
            return f"M{mate} (white mates)"
        return f"-M{abs(mate)} (black mates)"
    if cp is None:
        return "0.00"
    pawns = cp / 100.0
    sign = "+" if pawns >= 0 else ""
    return f"{sign}{pawns:.2f}"


def _uci_to_san(fen: str, uci: str) -> str:
    try:
        board = chess.Board(fen)
        move = chess.Move.from_uci(uci)
        return board.san(move)
    except Exception:
        return uci


def _format_recent_moves(recent: List[dict]) -> str:
    if not recent:
        return "(none yet)"
    parts = []
    for m in recent:
        san = m.get("san", "?")
        cat = m.get("category", "?")
        cp = m.get("cp_loss")
        if cp is not None and cp > 0:
            parts.append(f"{san} ({cat}, -{cp}cp)")
        else:
            parts.append(f"{san} ({cat})")
    return ", ".join(parts)


def build_coach_prompt(
    *,
    fen_before: str,
    user_move_uci: str,
    history_san: List[str],
    recent_user_moves: List[dict],
    category: str,
    cp_loss: int,
    score_cp_before: Optional[int],
    score_cp_after: Optional[int],
    mate_before: Optional[int],
    mate_after: Optional[int],
    best_move_uci: Optional[str],
    elo: int,
    game_over: bool,
    result: Optional[str],
    opening_eco: Optional[str] = None,
    opening_name: Optional[str] = None,
) -> str:
    move_san = _uci_to_san(fen_before, user_move_uci)

    tail = history_san[-6:]
    history_text = " ".join(tail) if tail else "(start of game)"

    eval_before = _format_eval(score_cp_before, mate_before)
    eval_after = _format_eval(score_cp_after, mate_after)

    is_opening = len(history_san) <= 6
    phase = "opening" if is_opening else ("middlegame" if len(history_san) <= 40 else "endgame")

    hide_best = category in ("best", "excellent")

    recent_text = _format_recent_moves(recent_user_moves)

    player_color = "White" if chess.Board(fen_before).turn == chess.WHITE else "Black"
    lines = [
        f"Context: The player is playing {player_color} against an engine at approx. {elo} Elo.",
        f"Phase: {phase}",
    ]

    if opening_name:
        eco_part = f"{opening_eco} - " if opening_eco else ""
        lines.append(f"Opening: {eco_part}{opening_name}")
        if is_opening:
            lines.append("(Mention the opening only if it helps explain this move.)")

    lines.extend([
        f"Recent moves (both sides): {history_text}",
        f"Player's recent moves with feedback: {recent_text}",
        "",
        f"Player just played: {move_san} (uci {user_move_uci})",
        f"Eval before the move (white's POV): {eval_before}",
        f"Eval after the move (white's POV):  {eval_after}",
        f"Centipawn loss for the player: {cp_loss}",
        f"Category: {category}",
    ])

    if not hide_best and best_move_uci:
        best_san = _uci_to_san(fen_before, best_move_uci)
        lines.append(f"Engine's preferred move: {best_san}")

    if game_over:
        lines.append("")
        lines.append(f"The game is over. Result: {result or 'unknown'}.")
        lines.append("Write a single warm sentence about the outcome instead of analysing the move.")

    return "\n".join(lines)
