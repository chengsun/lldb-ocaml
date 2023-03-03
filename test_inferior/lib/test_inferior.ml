open! Core
open! Async

module Incr = struct
  let rpc =
    Rpc.Rpc.create
      ~name:"incr"
      ~version:1
      ~bin_query:[%bin_type_class: int]
      ~bin_response:[%bin_type_class: int]
  ;;

  let implementation = Rpc.Rpc.implement rpc (fun () query -> return (query + 1))
end

let[@cold] my_function x =
  let _ = List.init 10000000 ~f:(fun i -> i) |> List.fold ~init:0 ~f:(+) in
  let _ = Sys.opaque_identity x in ()
;;

let command =
  Command.async
    ~summary:"a test inferior program"
    (let%map_open.Command () = return () in
     fun () ->
       let%bind server =
         Rpc.Connection.serve
           ~implementations:
             (Rpc.Implementations.create_exn
                ~implementations:[ Incr.implementation ]
                ~on_unknown_rpc:`Close_connection)
           ~initial_connection_state:(fun _ _ -> ())
           ~where_to_listen:Tcp.Where_to_listen.of_port_chosen_by_os
           ()
       in
       let port = Tcp.Server.listening_on server in
       print_s [%sexp "Server started", { port : int }];
       let%bind () =
         Rpc.Connection.with_client
           (Tcp.Where_to_connect.of_host_and_port
              (Host_and_port.create ~host:"localhost" ~port))
           (fun conn ->
             Deferred.forever 0 (fun i ->
                  my_function "AAAAAAAAAAAAAAAAAAAAAAAAA";
               if i < 10 || i % 10000 = 0 then print_s [%sexp "Progress", { i : int }];
               Rpc.Rpc.dispatch_exn Incr.rpc conn i);
             Deferred.never ())
         >>| Result.ok_exn
       in
       return ())
;;
