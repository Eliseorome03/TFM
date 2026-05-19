package com.example.demo.model;

public class Cliente {

    private int aniosConNosotros;
    private boolean vip;

    public Cliente() {}

    public int getAniosConNosotros() {
        return aniosConNosotros;
    }

    public void setAniosConNosotros(int aniosConNosotros) {
        this.aniosConNosotros = aniosConNosotros;
    }

    public boolean isVip() {
        return vip;
    }

    public void setVip(boolean vip) {
        this.vip = vip;
    }
}