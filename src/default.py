import appuifw, e32, e32dbm, globalui, btsocket, urllib, thread, re, os, ftpserver

class sypFTP(object):
  
  """ Init sypFTP object """
  def __init__(self):
    
    """ Get info about drives in Symbian OS """
    self.appDrive()
    self.generateDriveList()
    
    """ Set app info """
    self.__NAME__     = u"sypFTP"
    self.__VERSION__  = u"0.1.0"
    self.__AUTHOR__   = u"Intars Students"
    self.__EMAIL__    = u"the.mobix@gmail.com"
    self.__URL__      = u"http://code.google.com/p/sypftp/"
    self.__UPDATE__   = u"http://sypftp.googlecode.com/svn/trunk/VERSION"
    
    self.log_arr      = []
    self.ftpd_running = False
    self.ftpd_auto    = True
    self.db           = u"%s\\options.db" % self.__APPDIR__
    
    """ Set default user options and load custom ones (if there is some) """
    self.default = {
      u"port"  : 21,
      u"user"  : u"user",
      u"pass"  : u"12345",
      u"dir"   : u"C:\\"
    }
    
    self.getOptions()
    
    """ Hook FTP server log's to main console output """
    ftpserver.log       = self.log
    ftpserver.logline   = self.log
    ftpserver.logerror  = self.log
    
    """ Set look and feel of main console """
    self.uiConsole = appuifw.Text()
    self.uiPopup = globalui
    
    appuifw.app.title = self.__NAME__
    self.uiMenu(["connect", "options", "about", "exit"])
    appuifw.app.body = self.uiConsole
    appuifw.app.screen = "normal"
    appuifw.app.exit_key_handler = self.exit
    
    """ Set look and feel of options """
    self.uiOptions = appuifw.Form(
      [
        (u"Port",   "number", self.default["port"]),
        (u"User",   "text",   self.default["user"]),
        (u"Paswd",  "text",   self.default["pass"]),
        (u"Dir.",   "combo",  (self.available_drives, self.available_drives.index(self.default["dir"])))
      ],
      appuifw.FFormEditModeOnly
    )
    self.uiOptions.save_hook = self.saveOptions
    
    """ Start console output thread """
    self.console_thread = e32.Ao_timer()
    self.console_thread.after(0, self.console)
    
    """ Start up network (if it possible) """
    self.networking()
    
    """ If there is network connection, start ftp server """
    if self.getIP() != False:
      self.ftp_server_start()
    
    """ Start network check thread """
    self.network_thread = e32.Ao_timer()
    self.network_thread.after(10, self.network_deamon)
    
    """ Update thread """
    self.update_thread = e32.Ao_timer()
    
    """ Lock and load """
    self.app_lock = e32.Ao_lock()
    self.app_lock.wait()
  
  """ Console output thread """
  def console(self):
    
    if len(self.log_arr):
      for index, msg in enumerate(self.log_arr):
        self.uiConsole.add(msg)
        self.log_arr.pop(index)
    
    self.console_thread.after(0, self.console)
  
  """ Send log message to console output """
  def log(self, msg):
    
    if msg:
      self.log_arr.append(u"%s\n" % (msg))
      
  """ Some debugging needs to be done """
  def debug(self, command):
    
    if command:
      self.log(eval("dir(" + command + ")"))
  
  """ Generate sypFTP application folder """
  def appDrive(self):
    
    try:
      m = re.match("^([A-Z])\:", os.getcwd())
      self.__DRIVE__ = m.group(1)
    except:
      self.__DRIVE__ = "C:"
    
    self.__APPDIR__ = u"%s:\\data\\sypFTP" % self.__DRIVE__
    
    try:
      os.makedirs(self.__APPDIR__)
    except:
      pass
    
  """ Generate list of drives available inside Symbian OS from whom user can choose of """
  def generateDriveList(self):
    
    self.available_drives = []
    
    for drive in e32.drive_list():
      try:
        os.listdir(drive + "\\")
        self.available_drives.append(u"%s\\" % drive)
      except:
        pass
    
  """ Get IP of current network connection """
  def getIP(self):
    
    try:
      return self.apo.ip()
    except:
      return False
  
  """ Start up network connection """
  def networking(self):
    
    self.log("Connecting to network ...")
    
    try:
      self.apid = btsocket.select_access_point()
      self.apo  = btsocket.access_point(self.apid)
      
      self.apo.start()
      
      self.log("done.")
      self.uiMenu(["start", "restart", "stop", "options", "update", "about", "exit"])
      
    except:
      self.log("failed.")
      self.uiMenu(["connect", "options", "about", "exit"])
  
  """ Check every 10 sec is there a network connection open, else try to reconnect.
  If that fails, then if FTP server is running, turn it off."""
  def network_deamon(self):
    
    if self.getIP() == False and self.ftpd_running:
      
      self.log("Lost network connection, reconnecting ...")
      try:
        self.apo.start()
        self.log("Reconnected successfully")
      except:
        pass
      
      if self.getIP() == False:
        
        try:
          self.ftpd.close_all()
        except:
          pass
        
        try:
          self.apo.stop()
          self.apo.start()
        except:
          pass
        
        if self.getIP() == False and self.ftpd_running:
          self.ftpd_running = False
          self.uiMenu(["connect", "start", "options", "update", "about", "exit"])
          
        elif self.getIP() != False and self.ftpd_running:
          self.ftp_server_start()
        
    self.network_thread.after(10, self.network_deamon)
  
  """ Stop FTP server, network connection and exit from sypFTP (bye) """
  def exit(self):
    
    try:
      self.ftp_server_stop()
      self.apo.stop()
    except:
      pass
      
    try:
      self.console_thread.cancel()
      self.network_thread.cancel()
    except:
      pass
    
    self.app_lock.signal()
  
  """ Show simple about message for 10 sec """
  def showAbout(self):
    
    self.uiPopup.global_msg_query(
      (
      self.__NAME__ + " v." + self.__VERSION__ + "\n" +
      "by " + self.__AUTHOR__ + "\n" + 
      self.__EMAIL__ + "\n" +
      self.__URL__
      ),
      u"About",
      10
    )
  
  """ Check for update and if there is something new, take user to Web browser to download package """
  def showUpdate(self):
  
    self.log("Checking for update ...")
    
    XML   = ""
    ERROR = False
    
    try:
      XML = urllib.urlopen(self.__UPDATE__).read()
    except:
      pass
    
    if XML != "":
      pys60_version = ""
      for v in e32.pys60_version_info[:3]:
        pys60_version += str(v) + "\."
      
      v = re.search("<version>(\d+\.\d+\.\d+)<\/version>", XML)
      u = re.search("<url build=\"" + pys60_version + "\">(.*?)<\/url>", XML)
      
      if v != None:
        if v.group(1) == self.__VERSION__:
          self.log("sypFTP is up-to-date.")
          
        elif u != None:
          self.log("Updating to sypFTP v." + v.group(1) + " ...")
          self.launchBrowser(u.group(1))
          
        else:
          self.log("\nThere aren't any builds for PyS60 " + pys60_version.replace("\\", "") + " You should update to newer version of PyS60 or try to build sypFTP for this one.")
          
      else:
        ERROR = True
      
    else:
      ERROR = True
      
    if ERROR:
      self.log("Couldn't fetch update now.")
  
  """ Opens update checker in it's own thread """
  def update_deamon(self):
    self.update_thread.after(0, self.showUpdate)
  
  """ Launch build-in Web browser """
  def launchBrowser(self, url):
    try:
      e32.start_exe("z:\\system\\programs\\apprun.exe", "z:\\System\\Apps\\Browser\\Browser.app \"%s\"" % url , 1)
    except:
      try:
        e32.start_exe("BrowserNG.exe", " \"4 %s %s\"" % (url, str(self.apid)), 1)
      except:
        self.log("Couldn't launch a Web browser.")
  
  """ Create main menu from available items """
  def uiMenu(self, struc):
    allstruc = [
      ["connect", (u"Connect to network",   self.networking)],
      ["start",   (u"Start server",         self.ftp_server_start)],
      ["stop",    (u"Stop server",          self.ftp_server_stop)],
      ["restart", (u"Restart server",       self.ftp_server_restart)],
      ["options", (u"Options",              self.showOptions)],
      ["update",  (u"Update",               self.update_deamon)],
      ["about",   (u"About",                self.showAbout)],
      ["exit",    (u"Exit",                 self.exit)],
    ]
    
    selstruc = []
    
    for name, bind in allstruc:
      if struc.count(name):
        if name == "connect" and self.getIP() == False:
          selstruc.append(bind)
          
        elif name == "start" and self.getIP() != False and self.ftpd_running == False:
          selstruc.append(bind)
          
        elif name in ["stop", "restart"] and self.ftpd_running == True:
          selstruc.append(bind)
        
        elif name == "update" and self.getIP() != False:
          selstruc.append(bind)
          
        elif name not in ["connect", "start", "stop", "restart"]:
          selstruc.append(bind)
    
    if len(selstruc):
      appuifw.app.menu = selstruc
      
  """ Show options dialogue """
  def showOptions(self):
    
    self.generateDriveList()
    self.uiOptions.execute()
  
  """ Load options from database file and overwrite them with default ones or 
  if database doesn't exist create one """
  def getOptions(self):
    
    try:
      db = e32dbm.open(self.db, "r")
      
      for key, value in db.items():
        if key == "port":
          self.default[key] = int(value)
          
        elif key == "dir":
          try:
            self.available_drives.index((u"%s" % value))
          except:
            value = self.default["dir"]
          
          self.default[key] = (u"%s" % value)
          
        else:
          self.default[key] = (u"%s" % value)
      
      db.close()
      
    except Exception, e:
      self.setOptions()
  
  """ Save user options to database file or create new one if there isn't such """
  def setOptions(self):
    
    db = e32dbm.open(self.db, "c")
    for key in self.default.keys():
      db[key] = str(self.default[key])
    
    db.close()
  
  """ Check if entered user options are correct and if so, save them to database """
  def saveOptions(self, arg):
    
    if int(arg[0][2]) < 0 or int(arg[0][2]) > 65535:
      self.uiPopup.global_note(u"Port must be in range of 0 - 65535")
      return False
    
    else:
      self.default["port"] = int(arg[0][2])
    
    if re.search("^[a-zA-Z0-9_]+$", (u"%s" % arg[1][2])) == None:
      self.uiPopup.global_note(u"You can only use A-z, 0-9 and underscore in user name")
      return False
    
    else:
      self.default["user"] = (u"%s" % arg[1][2])
      
    if re.search("^[a-zA-Z0-9_@#$%^&+=]+$", (u"%s" % arg[2][2])) == None:
      self.uiPopup.global_note(u"You can only use A-z, 0-9 and any of them (_@#$%^&+=) in password")
      return False
      
    else:
      self.default["pass"] = (u"%s" % arg[2][2])
    
    self.default["dir"] = (u"%s" % self.available_drives[arg[3][2][1]])
    
    self.setOptions()
    self.uiPopup.global_note(u"Options saved", "info")
    return True
  
  """ Start FTP server """
  def ftp_server_start(self):
    
    if self.getIP() != False:
      self.ftpd_thread = thread.start_new_thread(self.ftp_server_deamon, ())
      
    else:
      try:
        self.apo.start()
      except:
        pass
      
      if self.getIP() != False:
        self.ftpd_thread = thread.start_new_thread(self.ftp_server_deamon, ())
      
      else:
        self.uiMenu(["connect", "options", "about", "exit"])
  
  """ Stop FTP server """
  def ftp_server_stop(self):
    
    try:
      self.ftpd.close_all()
    except:
      pass
    
    self.ftpd_running = False
    self.uiMenu(["connect", "start", "options", "update", "about", "exit"])
  
  """ Restart FTP server """
  def ftp_server_restart(self):
    
    self.ftp_server_stop()
    self.ftp_server_start()
  
  """ FTP server deamo """
  def ftp_server_deamon(self):
    
    try:
      if self.ftpd_running == False:
        
        self.ftp_authorizer   = ftpserver.DummyAuthorizer()
        self.ftp_authorizer.add_user(self.default["user"], self.default["pass"], self.default["dir"], perm='elradfmw')
        
        self.ftp_handler            = ftpserver.FTPHandler
        self.ftp_handler.authorizer = self.ftp_authorizer
        self.ftp_handler.banner     = self.__NAME__
        
        self.ftpd = ftpserver.FTPServer((self.getIP(), self.default["port"]), self.ftp_handler)
        self.ftpd.max_cons        = 256
        self.ftpd.max_cons_per_ip = 5
        self.ftpd.timeout         = 0
        self.ftpd_running         = True
        
        self.uiMenu(["restart", "stop", "options", "update", "about", "exit"])
        self.ftpd.serve_forever()
        
        self.ftpd_running = False
        self.log("FTP server stopped.")
        self.uiMenu(["connect", "start", "options", "update", "about", "exit"])
        
    except Exception, e:
      if self.ftpd_auto:
        self.log("Couldn't auto start FTP server. Do it manually.")
      else:
        self.log("FTP server error: %s" % e)
      
      self.ftpd_auto    = False
      self.ftpd_running = False
      self.uiMenu(["connect", "start", "options", "update", "about", "exit"])

""" Start up sypFTP """
if __name__ == '__main__':
  sypFTP()
