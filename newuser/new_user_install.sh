echo "export https_proxy=http://child-prc.intel.com:913" >> ~/.bashrc
echo "export http_proxy=http://child-prc.intel.com:913" >> ~/.bashrc
echo "export ftp_proxy=ftp://child-prc.intel.com:913/" >> ~/.bashrc
source ~/.bashrc
sudo -E apt-get upgrade
sudo -E apt-get install meld
sudo -E apt-get install openssh-client
sudo -E apt-get install git-lfs
echo "----------scp git ssh config----------\n"
scp luwei@10.67.109.200:~/.gitconfig ~/
scp luwei@10.67.109.200:~/.ssh/* ~/.ssh/
sudo scp luwei@10.67.109.200:/usr/bin/corkscrew /usr/bin/


