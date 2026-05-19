package com.example.demo.controller;

import com.example.demo.model.Pedido;
import com.example.demo.service.DroolsService;
import org.springframework.web.bind.annotation.*;

@RestController
@RequestMapping("/rules")
public class RuleController {

    private final DroolsService service;

    public RuleController(DroolsService service) {
        this.service = service;
    }

    @PostMapping
    public Pedido ejecutar(@RequestBody Pedido pedido) {
        return service.ejecutar(pedido);
    }
}
