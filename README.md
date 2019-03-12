Implementation of the Simple Transfer Protocol (STP) which is essentially TCP implemented using UDP.

Requires Python 3.6+

To run first navigate into the folder and run the following command:

    python receiver.py [receiver_port] [file_name_out]
    
Then using a separate terminal window run the following command (this can take place on another computer):

    python sender.py [receiver_host_ip] [receiver_port] [file_name_in]
    
There are many optional arguments to use when running 'sender.py' refer to page 5 of the 'assign_spec_2.pdf' document
