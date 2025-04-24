

public class Benchmark7 {
    public static void main(String[] args) {
        // fetch input
        Character input_1_0 = args[0].charAt(0);
        Character input_2_0 = args[1].charAt(0);


        // Perform computation         
        String output_1 = input_1_0.toString();
        String output_2 = input_2_0.toString();

        
        // Compare output
        if (output_1.equals("1") && output_2.equals(" ")) {
            System.out.println("Correct :)");
        } else {
            System.exit(1);
        }
    }
}

