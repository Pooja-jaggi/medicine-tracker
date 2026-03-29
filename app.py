from flask import Flask,render_template,request,redirect,url_for,flash,session
from flask_bcrypt import Bcrypt
import sqlite3
from datetime import datetime,timedelta
from flask_mail import Mail,Message 
from dotenv import load_dotenv
import os
load_dotenv()
app=Flask( __name__)
app.secret_key='meditrack123'
app.config['MAIL_SERVER']='smtp.gmail.com'
app.config['MAIL_PORT']=587
app.config['MAIL_USE_TLS']=True
app.config['MAIL_USERNAME']=os.getenv('MAIL_USERNAME')
app.config['MAIL_PASSWORD']=os.getenv('MAIL_PASSWORD')
mail=Mail(app)

bcrypt=Bcrypt(app)
def get_db():
    conn=sqlite3.connect('medicine.db')
    conn.row_factory=sqlite3.Row
    return conn
def send_reminder_email(user_email,user_name,expired,expiring,low_stock):
    subject='💊 MediTrack - Your Daily Medicine Reminder'
    body=f'Hello {user_name},\n\n'
    body+='Here is your daily medicine summary:\n\n'
    if expired:
        body+='🚨 EXPIRED MEDICINES:\n'
        for med in expired:
            body+=f"-{med['name']} (expired on {med['expiry_date']})\n"
            body+='\n'
    if expiring:
        body+='⚠️ EXPIRING SOON:\n'
        for med in expiring:
            body+=f" -{med['name']} (expires on {med['expiry_date']})\n"
            body+='\n'
    if low_stock:
        body+='📦 LOW STOCK:\n'
        for med in low_stock:
            body+=f" -{med['name']} (only{med['quantity']}left)\n"
            body+='\n'
    body+='Please take action on the above medicine .\n\n'
    body+='stay healthy!\nMeditrack Team'
    msg=Message(
        subject=subject,
        sender=app.config['MAIL_USERNAME'],
        recipients=[user_email],
        body=body
    )
    mail.send(msg)
@app.route('/')
def home():
    return render_template('index.html')
@app.route('/signup',methods=['GET','POST'])
def signup():
    if request.method=='POST':
        name=request.form['name']
        email=request.form['email']
        password=request.form['password']
        confirm_password=request.form['confirm_password']
        if password!=confirm_password:
            flash('Password do not match!','error')
            return redirect(url_for('signup'))
        hashed_password=bcrypt.generate_password_hash(password).decode('utf-8')
        try:
            conn=get_db()
            conn.execute('INSERT INTO users(name,email,password) VALUES(?,?,?)',
                         (name,email,hashed_password))
            conn.commit()
            conn.close()
            flash('Account created succesfully Please login. ','success')
            return redirect(url_for('login'))
        except Exception as e:
            import traceback
            traceback.print_exc()
            flash(str(e),'error')
            return redirect(url_for('signup'))
    return render_template('signup.html')
@app.route('/login',methods=['GET','POST'])
def login():
    if request.method=="POST":
        email=request.form['email']
        password=request.form['password']
        conn=get_db()
        user=conn.execute('SELECT* FROM users WHERE email=?',(email,)).fetchone()
        conn.close()
        if user and bcrypt.check_password_hash(user['password'],password):
            session['user_id']=user['id']
            session['user_name']=user['name']
            flash('Login successful!Welcome'+user['name']+'!','success')
            return redirect(url_for('dashboard'))
        else:
            flash('Invalid email or password!','error')
            return redirect(url_for('login'))
    return render_template('login.html')
@app.route('/dashboard')
def dashboard():
    if'user_id'not in session:
        flash('Please login first!','error')
        return redirect(url_for('login'))
    conn=get_db()
    user_id=session['user_id']
    medicines=conn.execute(
        'SELECT * FROM medicines WHERE user_id=?',(user_id,)).fetchall()
    today=datetime.today().date()
    thirty_days=today+timedelta(days=30)
    total=len(medicines)
    expired=0
    expiring=0
    safe=0
    expiring_medicines=[]
    for med in medicines:
        exp_date=datetime.strptime(med['expiry_date'],'%Y-%m-%d').date()
        if exp_date<today:
            expired+=1
        elif exp_date<=thirty_days:
            expiring+=1
            expiring_medicines.append(med)
        else:
            safe+=1
    conn.close()
    return render_template('dashboard.html',
                           user_name=session['user_name'],
                           total=total,
                           expired=expired,
                           expiring=expiring,
                           safe=safe,
                           expiring_medicines=expiring_medicines
                        )  
@app.route('/logout')
def logout():
    session.clear()
    flash('logged out sucessfully!','success')
    return redirect(url_for('login'))
@app.route('/add-medicine',methods=['GET','POST'])
def add_medicine():
    if 'user_id' not in session:
        flash('Please login first!','error')
        return redirect(url_for('login'))
    if request.method=='POST':
        name=request.form['name']
        manufacture_date=request.form['manufacture_date']
        expiry_date=request.form['expiry_date']
        quantity=request.form['quantity']
        dosage=request.form['dosage']
        frequency=request.form['frequency']
        when_to_take=request.form['when_to_take']
        purpose=request.form['purpose']
        side_effects=request.form['side_effects']
        user_id=session['user_id']
        conn=get_db()
        conn.execute('''
                     INSERT INTO medicines
                     (name,manufacture_date,expiry_date,quantity,dosage,frequency,when_to_take,purpose,side_effects,user_id)
                     VALUES(?,?,?,?,?,?,?,?,?,?)''',(name,manufacture_date,expiry_date,quantity,dosage,frequency,when_to_take,purpose,side_effects,user_id))
        conn.commit()
        conn.close()
        flash('Medicine added succesfully!','success')
        return redirect(url_for('dashboard'))
    return render_template('add_medicine.html')
@app.route('/medicines')
def medicines():
    if 'user_id' not in session:
        flash('Please login first!','error')
        return redirect(url_for('login'))
    conn=get_db()
    meds=conn.execute(
        'SELECT * FROM medicines WHERE user_id=?',(session['user_id'],)).fetchall()
    conn.close()
    today=datetime.today().date()
    thirty_days=today+timedelta(days=30)
    medicines_list=[]
    for med in meds:
        med=dict(med)
        exp_date=datetime.strptime(med['expiry_date'],'%Y-%m-%d').date()
        med['is_expired']=exp_date<today
        med['is_expiring']=today<=exp_date<=thirty_days
        frequency=med.get('frequency','daily') 
        if frequency=='weekly':
            med['low_stock']=med['quantity']<=2
        else:
            med['low_stock']=med['quantity']<=4
        if med['is_expired']:
            med['row_class']='expired-row'
        elif med['is_expiring']:
            med['row_class']='expiring-row'
        else:
            med['row_class']=''  
        medicines_list.append(med)
    return render_template('medicines.html',medicines=medicines_list)
@app.route('/take-medicine/<int:medicine_id>',methods=['POST'])
def take_medicine(medicine_id):
    if 'user_id'not in session:
        return redirect(url_for('login'))
    conn=get_db()
    med=conn.execute(
        'SELECT * FROM medicines WHERE id=? AND user_id=?',
        (medicine_id,session['user_id'])
        
    ).fetchone()
    if med:
        dosage=med['dosage']or 1
        new_quantity=med['quantity']-dosage
        if new_quantity < 0:
            new_quantity=0 
        conn.execute(
            'UPDATE medicines SET quantity=? WHERE id=?',
            (new_quantity,medicine_id)
        )
        conn.commit()
        frequency=med['frequency'] or'daily'
        if frequency =='weekly' and new_quantity<=2:
            flash(f"⚠️ Low stock alert! Only {new_quantity} left for {med['name']}. Please restock!", 'error')
        elif frequency !='weekly' and new_quantity<=4:
             flash(f"⚠️ Low stock alert! Only {new_quantity} left for {med['name']}. Please restock!", 'error')
        else:
            flash(f"✅ Taken! {med['name']} quantity updated to {new_quantity}.", 'success')
    conn.close()
    return redirect(url_for('medicines'))
@app.route('/reminders')
def reminders():
    if 'user_id' not in session:
        flash('Please login first!', 'error')
        return redirect(url_for('login'))

    conn = get_db()
    meds = conn.execute(
        'SELECT * FROM medicines WHERE user_id = ?',
        (session['user_id'],)
    ).fetchall()
    conn.close()

    today = datetime.today().date()
    thirty_days = today + timedelta(days=30)

    expired_medicines = []
    expiring_medicines = []
    low_stock_medicines = []

    for med in meds:
        med = dict(med)
        exp_date = datetime.strptime(med['expiry_date'], '%Y-%m-%d').date()

        if exp_date < today:
            expired_medicines.append(med)
        elif exp_date <= thirty_days:
            med['days_left'] = (exp_date - today).days
            expiring_medicines.append(med)

        frequency = med.get('frequency', 'daily')
        if frequency == 'weekly':
            if med['quantity'] <= 2:
                low_stock_medicines.append(med)
        else:
            if med['quantity'] <= 4:
                low_stock_medicines.append(med)

    return render_template('reminders.html',
        expired_medicines=expired_medicines,
        expiring_medicines=expiring_medicines,
        low_stock_medicines=low_stock_medicines
    )
@app.route('/delete-medicine/<int:medicine_id>',methods=['POST'])
def delete_medicine(medicine_id):
    if 'user_id'not in session:
        return redirect(url_for('login'))
    conn=get_db()
    conn.execute(
        'DELETE FROM medicines WHERE id=? AND user_id=?',
        (medicine_id,session['user_id'])
        )
    conn.commit()
    conn.close()
    flash('Medicine deleted successfully!','success')
    return redirect(url_for('medicines'))
@app.route('/edit-medicine/<int:medicine_id>',methods=['GET','POST'])
def edit_medicine(medicine_id):
    if 'user_id' not in session:
        flash('Please Login first!','error')
        return redirect(url_for('login'))
    conn=get_db()
    if request.method=='POST':
        name = request.form['name']
        manufacture_date = request.form['manufacture_date']
        expiry_date = request.form['expiry_date']
        quantity = int(request.form['quantity'])
        dosage = int(request.form['dosage']) if request.form['dosage'] else None
        frequency = request.form['frequency']
        when_to_take = request.form['when_to_take']
        purpose = request.form['purpose']
        side_effects = request.form['side_effects']
        conn.execute(''' 
                     UPDATE medicines SET
                     name=?,
                     manufacture_date=?,
                     expiry_date=?,
                     dosage=?,
                     quantity=?,
                     frequency=?,
                     when_to_take=?,
                     purpose=?,
                     side_effects=?
                     where id=? AND user_id=?
                     ''',(name,manufacture_date,expiry_date,quantity,dosage,frequency,when_to_take,purpose
                          ,side_effects,medicine_id,session['user_id']))
        conn.commit()
        conn.close()
        flash('Medicine updated succesfully!','success')
        return redirect(url_for('medicines'))
    med=conn.execute(
        'SELECT * FROM medicines WHERE id=? AND user_id=?',
        (medicine_id,session['user_id'])
    ).fetchone()
    conn.close()
    return render_template('edit_medicine.html',med=med)
@app.route('/send-reminders')
def send_reminders():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    conn=get_db()
    user=conn.execute(
        'SELECT * FROM users WHERE id=?',
        (session['user_id'],)
    ).fetchone()
    
    meds=conn.execute(
        'SELECT * FROM medicines WHERE user_id=?',
        (session['user_id'],)
    ).fetchall()
    conn.close()
    today=datetime.today().date()
    thirty_days=today+timedelta(days=30)
    
    expired=[]
    expiring=[]
    low_stock=[]
    
    for med in meds:
        med=dict(med)
        exp_date=datetime.strptime(med['expiry_date'],'%Y-%m-%d').date()
        
        if exp_date<today:
            expired.append(med)
        elif exp_date<=thirty_days:
            expiring.append(med)
        frequency=med.get('frequency','daily')
        if frequency=='weekly'and med['quantity']<=2:
            low_stock.append(med)
        elif frequency!='weekly'and med['quantity']<=4:
            low_stock.append(med)
    if not expired and not expiring and not low_stock:
        flash('All medicines are safe! No reminders needed.', 'success')
        return redirect(url_for('reminders'))


    try:
        send_reminder_email(user['email'],user['name'],expired,expiring,low_stock)
        flash('Reminder email send successfully! Check your inbox.','success')
    except Exception as e:
        flash(f'Email error:{str(e)}','error')
    return redirect(url_for('reminders'))
                

                   
if __name__=='__main__':
        app.run(debug=True)
        