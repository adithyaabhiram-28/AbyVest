import os
import markdown
import google.generativeai as genai
from flask import Blueprint, render_template, request, jsonify
from flask_login import login_required, current_user
from extensions import db
from models import Stock, ChatMessage

chat_bp = Blueprint('chat', __name__)


@chat_bp.route('/chat')
@login_required
def chat():
    chat_history = (
        ChatMessage.query.filter_by(user_id=current_user.id)
        .order_by(ChatMessage.id.asc())
        .all()
    )
    return render_template('chat.html', title='Chat', chat_history=chat_history)


@chat_bp.route('/chat/api', methods=['POST'])
@login_required
def chat_api():
    data = request.get_json(silent=True) or {}
    user_message = (data.get('message') or '').strip()
    if not user_message:
        return jsonify({'reply': 'Please enter a message.'}), 400
    if len(user_message) > 4000:
        return jsonify({'reply': 'Message is too long.'}), 400

    user_id = current_user.id

    stocks = Stock.query.filter_by(user_id=user_id).all()
    portfolio_context = "User's Portfolio:\n"
    if not stocks:
        portfolio_context += 'The user currently has no stocks.'
    else:
        for stock in stocks:
            portfolio_context += (
                f'- {stock.symbol}: {stock.shares} shares. '
                f'Buy: ${stock.purchase_price:.2f}. '
                f'Current: ${stock.current_price:.2f}.\n'
            )

    system_prompt = f"""You are Finley, an AI investment assistant.
    {portfolio_context}
    Give tailored advice based on the portfolio. End with a disclaimer that this is not professional financial advice."""

    db_message = (
        ChatMessage.query.filter_by(user_id=user_id)
        .order_by(ChatMessage.timestamp.desc())
        .limit(20)
        .all()
    )
    db_message.reverse()
    gemini_history = [
        {
            'role': 'user' if m.role == 'user' else 'model',
            'parts': [m.content],
        }
        for m in db_message
    ]

    try:
        api_key = os.getenv('GENAI_API_KEY')
        if not api_key:
            raise RuntimeError('GENAI_API_KEY is not configured')
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel(
            model_name='gemini-2.5-flash',
            system_instruction=system_prompt,
        )
        chat_session = model.start_chat(history=gemini_history)
        response = chat_session.send_message(user_message)
        ai_reply = markdown.markdown(response.text)
    except Exception:
        ai_reply = (
            'Sorry, Finley is temporarily unavailable. '
            'Please try again in a moment.'
        )

    db.session.add(ChatMessage(user_id=user_id, role='user', content=user_message))
    db.session.add(ChatMessage(user_id=user_id, role='assistant', content=ai_reply))
    db.session.commit()

    return jsonify({'reply': ai_reply})


@chat_bp.route('/chat/clear', methods=['POST'])
@login_required
def clear_chat():
    ChatMessage.query.filter_by(user_id=current_user.id).delete()
    db.session.commit()
    return jsonify({'status': 'cleared'})
