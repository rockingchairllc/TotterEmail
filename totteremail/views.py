from totteremail.models import *
from pyramid.view import view_config
from pyramid.httpexceptions import HTTPBadRequest, HTTPCreated
from gevent import Greenlet
from thread import start_new_thread
from datetime import datetime
import logging
import smtplib
from email.mime.text import MIMEText
def send_email(from_name, to_emails, bcc, subject, message):
    if not isinstance(to_emails, list):
        to_emails = [to_emails]
    msg = MIMEText(message.encode('utf-8'), 'plain', 'utf-8') 
    msg['Subject'] = subject
    msg['From'] = from_name
    if to_emails:
        msg['To'] = ','.join(to_emails)
    if bcc:
        msg['Bcc'] = ','.join(bcc)
    s = smtplib.SMTP('localhost')
    logging.info("sendimg mail to " + ','.join(to_emails) + ' bcc: ' + ','.join(bcc))
    s.sendmail(from_name, to_emails, msg.as_string())
    
def ensure_params(request, param_list):
    for param in param_list:
        if param not in request.params:
            raise HTTPBadRequest('Param missing: ' + param)
    return True
    
@view_config(route_name='home', renderer='templates/index.pt')
def index(request):
    return {'tree_data' : 'Its working.'}


def notify_immediate(from_email, event_id):
    # Notify all immediate subscribers of this eventType
    # and all ancestors of this eventType.
    session = DBSession()
    event = session.query(Event).filter(Event.id == event_id).one()
    eventType = event.type
    ancestorTypes = eventType.mp.query_ancestors().all()
    ancestorIDs = [ancestor.id for ancestor in ancestorTypes]
    subscribers = session.query(Subscription)\
        .filter(Subscription.type_id.in_([eventType.id] + ancestorIDs))\
        .filter(Subscription.frequency=='immediate').all()
    logging.log(str(len(subscribers)) + ' immediate subscribers to ' + eventType.name)
    emails = []
    for subscriber in subscribers:
        email = subscriber.email
        emails += [email]
        subscriber.last_sent = event.id # FIXME: Race condition. Only do this if last_sent < event.id
    # TODO: Is there a max limit on 
    send_email(from_email, [from_email], emails, event.subject, event.message)

@view_config(route_name='event', renderer='string')
def event(request):
    # Event parameters
    # 'subscription': <subscription name>
    # ['time' : <time of occurance>]
    # 'subject' : <event subject>
    # 'message' : <event message>
    ensure_params(request, ('subscription', 'subject', 'message'))
    subscription = request.params['subscription']
    session = DBSession()
    # Look up subscription, ensure validity.
    try: 
        eventType = session.query(EventType).filter(EventType.name==subscription).one()
    except NoResultFound:
        raise HTTPBadRequest('No subscription by that name: ' + subscription)
    
    # Store the event in the store
    event = Event(type=eventType, 
        when=request.params['time'] if 'time' in request.params else datetime.utcnow(), 
        subject=request.params['subject'],
        message=request.params['message']
    )
    session.add(event)
    session.flush()
    
    # Notify everyone who has an immediate subscription.
    #Greenlet.spawn(notify_immediate, request.registry.settings['email.from'], event)
    start_new_thread(notify_immediate,  (request.registry.settings['email.from'], event.id))
    return {}
    
@view_config(route_name='subscribe', renderer='string')
def subscribe(request):
    # Params:
    # 'subscription' : <subscription name>
    # 'email' : <email>
    # 'frequency' : 'daily' or 'instant'
    ensure_params(request, ('subscription', 'email', 'frequency'))
    subscription = request.params['subscription']
    frequency = request.params['frequency']
    email = request.params['email']
    session = DBSession()
    try: 
        eventType = session.query(EventType).filter(EventType.name==subscription).one()
    except NoResultFound:
        raise HTTPBadRequest('No subscription by that name: ' + subscription)
    
    subscriber = Subscription(email=email, type_id=eventType.id, frequency=frequency)
    session.add(subscriber)
    return HTTPCreated()

@view_config(route_name='create_sub', renderer='string')
def create_sub(request):
    # Params:
    # 'parent' : <parent name> or 'root'
    # 'name' : <subscription name>
    ensure_params(request, ('parent', 'name'))
    parent = request.params['parent']
    name = request.params['name']
    
    session = DBSession()
    # Verify parent's existence:
    try:
        if parent != 'root':
            parent = session.query(EventType).filter(EventType.name==parent).one()
        else:
            parent = None
    except NoResultFound:
        raise HTTPBadRequest('No subscription by that name: ' + parent)
    
    # Check if the mapping already exists:
    existing = session.query(EventType).filter(EventType.name==name).first()
    if existing and existing.parent != parent:
        raise HTTPBadRequest('Cant change subscription parent: ' + name)
    elif existing: 
        return {} # The subscription already exists. It's all good.
        
    # Add the subscription to our subscriptions (but its ok if it already exists).
    eventType = EventType(name=name, parent=parent)
    session.add(eventType)
    session.flush()
    return HTTPCreated()
    
@view_config(route_name='daily', renderer='string')
def daily(request):
    # Notify all daily subscribers with a digest:
    return {}