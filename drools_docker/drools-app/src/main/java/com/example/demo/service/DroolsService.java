package com.example.demo.service;

import com.example.demo.model.Pedido;
import org.kie.api.runtime.KieContainer;
import org.kie.api.runtime.KieSession;
import org.springframework.stereotype.Service;

@Service
public class DroolsService {

    private final KieContainer kieContainer;

    public DroolsService(KieContainer kieContainer) {
        this.kieContainer = kieContainer;
    }

    public Pedido ejecutar(Pedido pedido) {
        KieSession session = kieContainer.newKieSession("ksession-rules");
        session.insert(pedido);
        session.fireAllRules();
        session.dispose();
        return pedido;
    }
}
