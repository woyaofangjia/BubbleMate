from .database import (
    save_user_preference as _save_pref,
    get_user_preferences as _get_prefs,
    save_complaint as _save_comp,
    save_complaint_db as _save_comp_db,
    get_complaint_history as _get_comp_history,
    get_complaints as _get_comps,
    get_all_complaints as _get_all_comps,
    save_feedback as _save_fb,
    get_user_stats as _get_stats,
    save_session as _save_sess,
    get_user_by_session as _get_user_by_sess,
    save_knowledge as _save_knowledge,
    get_knowledge_list as _get_knowledge_list,
    get_knowledge_graph as _get_knowledge_graph,
    get_knowledge_graph_aggregated as _get_knowledge_graph_aggregated,
    add_knowledge_node as _add_knowledge_node,
    review_knowledge as _review_knowledge,
    delete_knowledge as _delete_knowledge,
    get_complaint_stats as _get_complaint_stats,
    resolve_complaint as _resolve_complaint,
)

def save_user_preference(user_id, key, value):
    _save_pref(user_id, key, value)

def get_user_preferences(user_id):
    return _get_prefs(user_id)

def save_complaint(user_id, complaint_data):
    _save_comp(user_id, complaint_data)

def save_complaint_db(user_id, complaint_type, description):
    _save_comp_db(user_id, complaint_type, description)

def get_complaint_history(user_id):
    return _get_comp_history(user_id)

def get_complaints(user_id):
    return _get_comps(user_id)

def get_all_complaints():
    return _get_all_comps()

def save_feedback(user_id, message_id, feedback_type):
    _save_fb(user_id, message_id, feedback_type)

def get_user_stats(user_id):
    return _get_stats(user_id)

def save_session(session_id, user_id):
    _save_sess(session_id, user_id)

def get_user_by_session(session_id):
    return _get_user_by_sess(session_id)

def save_knowledge(complaint_type, solution, compensation):
    _save_knowledge(complaint_type, solution, compensation)

def get_knowledge_list(reviewed_only=False):
    return _get_knowledge_list(reviewed_only)

def review_knowledge(id):
    _review_knowledge(id)

def delete_knowledge(id):
    _delete_knowledge(id)

def get_complaint_stats():
    return _get_complaint_stats()

def resolve_complaint(id):
    _resolve_complaint(id)

def get_knowledge_graph():
    return _get_knowledge_graph()

def get_knowledge_graph_aggregated():
    return _get_knowledge_graph_aggregated()

def add_knowledge_node(node_type, content, parent_id=None):
    return _add_knowledge_node(node_type, content, parent_id)