from flask import Flask, render_template, request, jsonify
import chess
import chess.engine
import chess.pgn
from io import StringIO

app = Flask(__name__)
board = chess.Board()
engine = chess.engine.SimpleEngine.popen_uci("stockfish/stockfish")  # ajusta ruta
engine.configure({"Skill Level": 0})

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/move", methods=["POST"])
def move():
    global board
    data = request.get_json()
    move_uci = data.get("move")

    try:
        # 🔁 Si no se recibe jugada (None), solo deja que el motor mueva
        if move_uci is None:
            if board.is_game_over():
                return jsonify({"ok": True, "game_over": True, "fen": board.fen()})

            result = engine.play(board, chess.engine.Limit(time=0.2))
            board.push(result.move)

            return jsonify({
                "ok": True,
                "move": result.move.uci(),
                "fen": board.fen(),
                "game_over": board.is_game_over()
            })

        # 👇 Si hay jugada del jugador
        move = chess.Move.from_uci(move_uci)
        if move in board.legal_moves:
            board.push(move)

            if board.is_game_over():
                return jsonify({"ok": True, "game_over": True, "fen": board.fen()})

            result = engine.play(board, chess.engine.Limit(time=0.2))
            board.push(result.move)

            return jsonify({
                "ok": True,
                "move": result.move.uci(),
                "fen": board.fen(),
                "game_over": board.is_game_over()
            })
        else:
            return jsonify({"ok": False, "error": "Movimiento ilegal"})
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)})

@app.route("/reset", methods=["POST"])
def reset():
    global board
    board = chess.Board()

    data = request.get_json(silent=True)
    motor_already_played = False
    level = data.get("level", 0)
    level = max(0, min(20, int(level)))
    engine.configure({"Skill Level": level})
    
    if data and data.get("color") == "black":
        # Si el usuario eligió negras, Stockfish juega primero
        result = engine.play(board, chess.engine.Limit(time=0.2))
        board.push(result.move)
        motor_already_played = True

    return jsonify({
        "fen": board.fen(),
        "motor_played": motor_already_played
    })

@app.route("/upload_pgn", methods=["POST"])
def upload_pgn():
    global board
    if "pgn_file" not in request.files:
        return jsonify({"ok": False, "error": "No se subió ningún archivo"})

    file = request.files["pgn_file"]

    try:
        pgn_text = file.read().decode("utf-8")
        pgn_io = StringIO(pgn_text)
        game = chess.pgn.read_game(pgn_io)
        board = game.end().board()
        return jsonify({"ok": True, "fen": board.fen()})
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)})

@app.route('/eval', methods=['POST'])
def eval_position():
    fen = request.json.get('fen')
    temp_board = chess.Board(fen)

    info = engine.analyse(temp_board, chess.engine.Limit(time=0.1))
    score = info["score"].white()

    if score.is_mate():
        eval_cp = 1000 if score.mate() > 0 else -1000
    else:
        eval_cp = score.score()

    def normalize(cp):
        cp = max(min(cp, 1000), -1000)
        return (cp + 1000) / 2000 * 100

    eval_percent = normalize(eval_cp)

    return jsonify({"eval_percent": eval_percent})

@app.route("/history", methods=["GET"])
def get_history():
    global board
    game = chess.pgn.Game()
    node = game

    for move in board.move_stack:
        node = node.add_variation(move)

    pgn_str = str(game)
    return jsonify({"pgn": pgn_str})
   
if __name__ == "__main__":
    app.run(debug=True)
